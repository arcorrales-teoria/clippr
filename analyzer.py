"""
analyzer.py — Full-video transcription + content-aware segment scoring.

Pipeline:
  1. Transcribe the ENTIRE video once with Whisper
  2. Detect natural speech scenes (split on long pauses)
  3. Score each scene by content density & vocabulary richness
  4. Return the top-N best start times spread across genuinely different parts
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# A pause longer than this (seconds) between words = scene boundary.
# Dynamically adjusted downward if no scenes are found at this level.
PAUSE_THRESHOLD = 0.8

# A scene must contain at least this many words to be considered
MIN_WORDS_PER_SCENE = 4


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_video(
    video_path: str,
    model_size: str,
    language: str,
    clip_length: float,
    num_clips: int,
    margin: float = 5.0,
    already_used: list[dict] | None = None,
) -> tuple[list[float], list[dict], list[dict]]:
    """
    Transcribe the full video and return the best clip start times.

    Args:
        video_path:   Path to the source video
        model_size:   Whisper model (tiny/base/small/medium/large)
        language:     ISO language code (es, en, …)
        clip_length:  Duration of each output clip in seconds
        num_clips:    How many clips to generate
        margin:       Seconds to skip at start and end of video
        already_used: List of {start, end} dicts from the registry

    Returns:
        (clip_starts, all_words, scenes)
        - clip_starts: list of float start times (len ≤ num_clips)
        - all_words:   full word list with timestamps (for subtitle reuse)
        - scenes:      list of scene dicts (for logging/debugging)
    """
    from transcriber import transcribe

    logger.info("Transcribing full video (this runs once for all clips)…")
    all_words = transcribe(video_path, model_size=model_size, language=language)
    logger.info(f"Full transcript: {len(all_words)} words")

    if not all_words:
        logger.warning("No speech detected — falling back to evenly spaced clips")
        starts = _evenly_spaced(
            _video_duration(video_path), clip_length, num_clips, margin, already_used or []
        )
        return starts, [], []

    total_duration = _video_duration(video_path)

    # Try progressively lower pause thresholds until we get enough scenes
    threshold = PAUSE_THRESHOLD
    scenes = []
    for attempt_threshold in [PAUSE_THRESHOLD, 0.6, 0.4, 0.2]:
        scenes = _detect_scenes(all_words, total_duration, margin, attempt_threshold)
        if len(scenes) >= num_clips:
            threshold = attempt_threshold
            break

    # Last resort: time-window fallback if speech has no clear pauses
    if len(scenes) < num_clips:
        logger.warning(
            f"Only {len(scenes)} speech scenes at threshold {threshold}s — "
            "using time-window segmentation as fallback"
        )
        scenes = _time_window_scenes(all_words, total_duration, margin, clip_length, num_clips)

    logger.info(f"Detected {len(scenes)} speech scenes (pause_threshold={threshold}s)")

    # Remove already-used time ranges from viable scene starts
    used = already_used or []

    # Score and rank scenes
    ranked = _rank_scenes(scenes, clip_length, total_duration, margin, used)
    logger.info(f"Ranked {len(ranked)} viable scenes")

    # Pick the top N spread across the video
    starts = _select_starts(ranked, num_clips, clip_length, total_duration, used)

    if len(starts) < num_clips:
        logger.warning(
            f"Only {len(starts)} content-distinct segments found "
            f"(requested {num_clips}). Some parts may already be used."
        )

    return starts, all_words, scenes


def words_for_segment(all_words: list[dict], start: float, end: float) -> list[dict]:
    """
    Slice only the words that fall within [start, end], re-zeroing their timestamps
    so they match the extracted segment (which starts at t=0).
    """
    segment_words = [
        {
            "word":  w["word"],
            "start": round(w["start"] - start, 3),
            "end":   round(w["end"]   - start, 3),
        }
        for w in all_words
        if w["start"] >= start and w["end"] <= end + 0.5
    ]
    return segment_words


# ── Scene detection ───────────────────────────────────────────────────────────

def _detect_scenes(words: list[dict], total_duration: float, margin: float,
                   pause_threshold: float = PAUSE_THRESHOLD) -> list[dict]:
    """
    Split words into scenes wherever there is a pause > PAUSE_THRESHOLD seconds.
    Each scene = {start, end, words, word_count, duration}.
    """
    if not words:
        return []

    scenes   = []
    current  = [words[0]]

    for prev, curr in zip(words, words[1:]):
        gap = curr["start"] - prev["end"]
        if gap >= pause_threshold:
            scene = _make_scene(current)
            if scene:
                scenes.append(scene)
            current = [curr]
        else:
            current.append(curr)

    if current:
        scene = _make_scene(current)
        if scene:
            scenes.append(scene)

    # Filter out scenes too close to the edges
    scenes = [s for s in scenes
              if s["start"] >= margin and s["end"] <= total_duration - margin]

    return scenes


def _time_window_scenes(
    words: list[dict],
    total_duration: float,
    margin: float,
    clip_length: float,
    num_clips: int,
) -> list[dict]:
    """
    Fallback: divide the usable timeline into num_clips * 2 windows and score
    each by word density. Returns scene dicts for each window.
    """
    usable_start = margin
    usable_end   = total_duration - margin
    usable        = usable_end - usable_start
    n_windows     = max(num_clips * 3, 10)
    window_size   = usable / n_windows

    scenes = []
    for i in range(n_windows):
        ws = usable_start + i * window_size
        we = ws + window_size
        window_words = [w for w in words if w["start"] >= ws and w["end"] <= we + 0.5]
        if len(window_words) >= MIN_WORDS_PER_SCENE:
            scenes.append({
                "start":      ws,
                "end":        we,
                "words":      window_words,
                "word_count": len(window_words),
                "duration":   window_size,
            })
    return scenes


def _make_scene(words: list[dict]) -> dict | None:
    if len(words) < MIN_WORDS_PER_SCENE:
        return None
    return {
        "start":      words[0]["start"],
        "end":        words[-1]["end"],
        "words":      words,
        "word_count": len(words),
        "duration":   words[-1]["end"] - words[0]["start"],
    }


# ── Scene scoring ─────────────────────────────────────────────────────────────

def _rank_scenes(
    scenes: list[dict],
    clip_length: float,
    total_duration: float,
    margin: float,
    used: list[dict],
) -> list[dict]:
    """
    Score each scene and return them sorted by score descending.
    Only includes scenes where a clip_length window is available and not already used.
    """
    scored = []

    for scene in scenes:
        # A viable clip can start anywhere from (scene.start) back up to
        # (scene.start) so that the clip covers this scene's opening words.
        # We use the scene start as the clip start.
        clip_start = max(margin, scene["start"])
        clip_end   = clip_start + clip_length

        if clip_end > total_duration - margin:
            clip_start = total_duration - margin - clip_length
            clip_end   = clip_start + clip_length

        if clip_start < margin:
            continue

        # Skip if this window overlaps an already-used segment
        if _overlaps_used(clip_start, clip_end, used):
            continue

        score = _score_scene(scene)

        scored.append({
            **scene,
            "clip_start": round(clip_start, 3),
            "score":      score,
        })

    # Sort by score descending
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


def _score_scene(scene: dict) -> float:
    """
    Higher score = more interesting segment.
    Factors:
      - Word density (words/second) — faster speech = more content
      - Vocabulary richness (unique words / total words)
      - Prefer medium-length scenes (not too short, not too long)
    """
    words    = scene["words"]
    duration = max(scene["duration"], 0.1)

    word_density  = len(words) / duration
    unique_ratio  = len({w["word"].lower() for w in words}) / max(len(words), 1)

    # Penalise very short scenes (< 5s) and very long ones (> 120s)
    length_penalty = 1.0
    if duration < 5:
        length_penalty = 0.4
    elif duration > 120:
        length_penalty = 0.7

    return word_density * (1 + unique_ratio) * length_penalty


# ── Start time selection ──────────────────────────────────────────────────────

def _select_starts(
    ranked: list[dict],
    num_clips: int,
    clip_length: float,
    total_duration: float,
    used: list[dict],
) -> list[float]:
    """
    Greedily pick up to num_clips start times from the ranked list,
    ensuring no two selected clips overlap each other or any used segment.
    Returns the list sorted chronologically.
    """
    selected: list[float] = []
    committed: list[dict] = list(used)  # treat already-used as off-limits

    for scene in ranked:
        if len(selected) >= num_clips:
            break

        cs = scene["clip_start"]
        ce = cs + clip_length

        if _overlaps_used(cs, ce, committed):
            continue

        selected.append(cs)
        committed.append({"start": cs, "end": ce})

    selected.sort()
    return selected


# ── Helpers ───────────────────────────────────────────────────────────────────

def _overlaps_used(start: float, end: float, used: list[dict]) -> bool:
    for u in used:
        # Overlap if intervals intersect (with 1s tolerance)
        if start < u["end"] - 1.0 and end > u["start"] + 1.0:
            return True
    return False


def _evenly_spaced(
    total_duration: float,
    clip_length: float,
    num_clips: int,
    margin: float,
    used: list[dict],
) -> list[float]:
    """Fallback: evenly space clips, skipping already-used segments."""
    from segment_registry import get_available_starts
    starts, _ = get_available_starts(
        "", total_duration, clip_length, num_clips, margin
    )
    return starts


def _video_duration(path: str) -> float:
    import subprocess
    r = subprocess.run(
        ["/opt/homebrew/opt/ffmpeg-full/bin/ffprobe",
         "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0
