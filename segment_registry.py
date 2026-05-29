"""
segment_registry.py — Persistent tracking of which video segments have been processed.

Stores a JSON file at outputs/segment_registry.json keyed by (filename + file_size).
When the same video is submitted again, already-used segments are skipped and
only fresh parts of the timeline are returned.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent / "outputs" / "segment_registry.json"


# ── Public API ────────────────────────────────────────────────────────────────

def get_available_starts(
    video_path: str,
    total_duration: float,
    clip_length: float,
    num_clips: int,
    margin: float = 5.0,
) -> tuple[list[float], int]:
    """
    Return a list of start times for `num_clips` non-overlapping, never-reused
    segments of `clip_length` seconds from `video_path`.

    If the video doesn't have enough fresh segments, returns as many as possible
    and the actual count.

    Returns:
        (list_of_start_times, actual_num_clips)
    """
    key       = _video_key(video_path)
    registry  = _load()
    used      = registry.get(key, {}).get("used_segments", [])

    # Build free intervals (start, end) that haven't been used yet
    free = _free_intervals(used, total_duration, margin)

    # Filter intervals that are at least clip_length long
    viable = [(s, e) for s, e in free if (e - s) >= clip_length]

    if not viable:
        logger.warning(f"No unused segments left in '{Path(video_path).name}'. "
                       "All parts have already been processed.")
        return [], 0

    # Greedily pick start positions spread across viable intervals
    starts = _pick_starts(viable, clip_length, num_clips)
    actual = len(starts)

    if actual < num_clips:
        logger.warning(
            f"Only {actual} fresh segments available (requested {num_clips}). "
            f"Video '{Path(video_path).name}' has been partially exhausted."
        )

    return starts, actual


def register_segments(
    video_path: str,
    total_duration: float,
    starts: list[float],
    clip_length: float,
    job_id: str,
) -> None:
    """
    Persist which segments were used by this job so they are excluded next time.
    """
    key      = _video_key(video_path)
    registry = _load()

    if key not in registry:
        registry[key] = {
            "filename":       Path(video_path).name,
            "file_size":      _file_size(video_path),
            "total_duration": total_duration,
            "used_segments":  [],
        }

    for i, start in enumerate(starts):
        registry[key]["used_segments"].append({
            "start":   round(start, 3),
            "end":     round(min(start + clip_length, total_duration), 3),
            "job_id":  job_id,
            "clip_no": i + 1,
        })

    _save(registry)
    logger.info(
        f"Registry updated for '{Path(video_path).name}': "
        f"{len(starts)} new segments saved."
    )


def get_used_summary(video_path: str) -> dict:
    """Return a summary of used segments for a video (for logging/UI purposes)."""
    key      = _video_key(video_path)
    registry = _load()
    entry    = registry.get(key)
    if not entry:
        return {"used_count": 0, "used_seconds": 0.0, "segments": []}

    segs = entry.get("used_segments", [])
    used_seconds = sum(s["end"] - s["start"] for s in segs)
    return {
        "used_count":   len(segs),
        "used_seconds": round(used_seconds, 1),
        "total_duration": entry.get("total_duration", 0),
        "segments": segs,
    }


def reset_video(video_path: str) -> None:
    """Clear all segment history for a video (start fresh)."""
    key      = _video_key(video_path)
    registry = _load()
    if key in registry:
        del registry[key]
        _save(registry)
        logger.info(f"Registry cleared for '{Path(video_path).name}'")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _video_key(path: str) -> str:
    """Stable identifier: filename + file size (avoids re-processing same content)."""
    p = Path(path)
    size = _file_size(path)
    return f"{p.name}::{size}"


def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _load() -> dict:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(registry: dict) -> None:
    REGISTRY_PATH.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _free_intervals(
    used_segments: list[dict],
    total_duration: float,
    margin: float,
) -> list[tuple[float, float]]:
    """
    Given a list of used {start, end} dicts, return the complementary
    free intervals within [margin, total_duration - margin].
    """
    usable_start = margin
    usable_end   = total_duration - margin

    if usable_end <= usable_start:
        return []

    # Sort used segments by start time
    used_sorted = sorted(used_segments, key=lambda s: s["start"])

    free   = []
    cursor = usable_start

    for seg in used_sorted:
        seg_start = max(seg["start"], usable_start)
        seg_end   = min(seg["end"],   usable_end)

        if seg_start > cursor:
            free.append((cursor, seg_start))

        cursor = max(cursor, seg_end)

    # Tail after last used segment
    if cursor < usable_end:
        free.append((cursor, usable_end))

    return free


def _pick_starts(
    viable: list[tuple[float, float]],
    clip_length: float,
    num_clips: int,
) -> list[float]:
    """
    Pick up to `num_clips` non-overlapping start positions spread across
    the viable free intervals.

    Strategy: fill each interval greedily from the start, distributing
    clip slots proportionally to interval length.
    """
    total_free = sum(e - s for s, e in viable)
    starts     = []

    for interval_start, interval_end in viable:
        if len(starts) >= num_clips:
            break

        interval_len = interval_end - interval_start

        # How many clips fit in this interval?
        slots_here = max(1, round(num_clips * interval_len / total_free))
        slots_here = min(slots_here, num_clips - len(starts))

        # How many actually fit without overlap?
        max_fit = int(interval_len // clip_length)
        slots_here = min(slots_here, max_fit)

        if slots_here <= 0:
            continue

        # Spread them evenly within the interval
        if slots_here == 1:
            # Centre the single clip in the interval
            mid   = (interval_start + interval_end) / 2
            start = max(interval_start, mid - clip_length / 2)
            start = min(start, interval_end - clip_length)
            starts.append(round(start, 3))
        else:
            # Evenly space start points so clips don't overlap
            # Available room after placing all clips end-to-end
            spare = interval_len - slots_here * clip_length
            gap   = spare / (slots_here - 1)          # gap between clip end and next clip start
            for i in range(slots_here):
                starts.append(round(interval_start + i * (clip_length + gap), 3))

    return starts[:num_clips]
