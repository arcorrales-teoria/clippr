#!/usr/bin/env python3
"""
server.py — Flask web server for the clippr UI.

Endpoints:
  POST /api/generate          — Upload video + settings, start job
  GET  /api/status/<job_id>   — Poll job status + logs
  GET  /api/results/<job_id>  — List output clips
  GET  /api/download/<job_id>/<filename> — Download a clip
  GET  /api/thumbnail/<job_id>/<filename> — Video thumbnail (first frame)
  GET  /                      — Serve index.html
"""

import json
import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.resolve()
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── In-memory job store ───────────────────────────────────────────────────────
# { job_id: { status, progress, stage, logs, clips, error } }
JOBS: dict[str, dict] = {}

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(BASE_DIR))
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])


@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/generate
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/preview", methods=["POST"])
def api_preview():
    """
    Fast analysis endpoint: upload video, get back speaker list with stats.
    Does NOT start rendering.
    """
    if "video" not in request.files:
        return jsonify(error="No video file"), 400

    f = request.files["video"]
    if not f.filename:
        return jsonify(error="Empty filename"), 400

    # Save upload
    preview_id  = str(uuid.uuid4())[:8]
    safe_name   = Path(f.filename).name
    input_path  = UPLOADS_DIR / f"{preview_id}_{safe_name}"
    f.save(str(input_path))

    try:
        lang  = request.form.get("lang", "es")
        model = request.form.get("model", "small")

        # Transcribe
        import sys; sys.path.insert(0, str(BASE_DIR))
        from transcriber import transcribe
        from analyzer import _detect_scenes, _video_duration

        words    = transcribe(str(input_path), model_size=model, language=lang)
        duration = _video_duration(str(input_path))

        # Detect speakers using pause-based segmentation
        speakers = _detect_speakers(words, duration)

        return jsonify(
            preview_id=preview_id,
            filename=safe_name,
            duration=round(duration, 1),
            word_count=len(words),
            speakers=speakers,
            input_path=str(input_path),
        )
    except Exception as e:
        import traceback
        return jsonify(error=str(e), traceback=traceback.format_exc()), 500


@app.route("/api/generate", methods=["POST"])
def api_generate():
    # Parse settings
    try:
        min_length   = int(request.form.get("min_length", 30))
        max_length   = int(request.form.get("max_length", 60))
        clip_length  = max_length  # use max_length as the target clip length
        num_clips    = int(request.form.get("num_clips", 3))
        subtitle_pos = request.form.get("subtitle_pos", "bottom")
        model        = request.form.get("model", "small")
        lang         = request.form.get("lang", "es")
        karaoke      = request.form.get("karaoke", "false").lower() == "true"
        show_subtitles = request.form.get("show_subtitles", "true").lower() == "true"
        selected_speakers_raw = request.form.get("selected_speakers", "[]")
        try:
            import json as _json
            selected_speakers = _json.loads(selected_speakers_raw)
        except Exception:
            selected_speakers = []
    except (ValueError, TypeError) as e:
        return jsonify(error=f"Invalid settings: {e}"), 400

    # Clamp values
    clip_length = max(10, min(300, clip_length))
    num_clips   = max(1,  min(20,  num_clips))

    # Save upload (or reuse from preview)
    job_id   = str(uuid.uuid4())[:8]
    job_dir  = OUTPUTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    provided_path = request.form.get("input_path", "")
    if provided_path and Path(provided_path).exists():
        input_path = Path(provided_path)
        # No need to save again
    else:
        if "video" not in request.files:
            return jsonify(error="No video file"), 400
        f = request.files["video"]
        if not f.filename:
            return jsonify(error="Empty filename"), 400
        safe_name  = Path(f.filename).name
        input_path = UPLOADS_DIR / f"{job_id}_{safe_name}"
        f.save(str(input_path))

    # Register job
    JOBS[job_id] = {
        "status":   "running",
        "progress": 0,
        "stage":    "tracking",
        "logs":     [],
        "clips":    [],
        "error":    None,
    }

    logger.info(
        f"[{job_id}] New job — {input_path.name} | "
        f"len={clip_length}s clips={num_clips} pos={subtitle_pos} "
        f"model={model} lang={lang}"
    )

    # Run in background thread
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, input_path, job_dir, clip_length, num_clips,
              subtitle_pos, model, lang),
        daemon=True,
    )
    thread.start()

    return jsonify(job_id=job_id)


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/status/<job_id>
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/status/<job_id>")
def api_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404
    return jsonify(
        status=job["status"],
        progress=job["progress"],
        stage=job["stage"],
        logs=job["logs"],
        error=job["error"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/results/<job_id>
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/results/<job_id>")
def api_results(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(error="Job not found"), 404
    return jsonify(clips=job["clips"])


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/download/<job_id>/<filename>
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/download/<job_id>/<path:filename>")
def api_download(job_id, filename):
    job_dir = OUTPUTS_DIR / job_id
    file_path = (job_dir / filename).resolve()
    # Security: ensure file is inside job_dir
    if not str(file_path).startswith(str(job_dir.resolve())):
        return jsonify(error="Forbidden"), 403
    if not file_path.exists():
        return jsonify(error="File not found"), 404
    return send_file(str(file_path), as_attachment=True, download_name=filename)


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/thumbnail/<job_id>/<filename>
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/api/thumbnail/<job_id>/<path:filename>")
def api_thumbnail(job_id, filename):
    job_dir   = OUTPUTS_DIR / job_id
    file_path = (job_dir / filename).resolve()
    if not str(file_path).startswith(str(job_dir.resolve())):
        return jsonify(error="Forbidden"), 403
    thumb_path = file_path.with_suffix(".thumb.jpg")
    if not thumb_path.exists() and file_path.exists():
        # Extract a single frame with FFmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(file_path),
             "-vf", "select=eq(n\\,0),scale=360:-1",
             "-vframes", "1", str(thumb_path)],
            capture_output=True,
        )
    if thumb_path.exists():
        return send_file(str(thumb_path), mimetype="image/jpeg")
    return jsonify(error="Thumbnail not available"), 404


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND JOB
# ══════════════════════════════════════════════════════════════════════════════
def _log(job_id: str, msg: str) -> None:
    """Append a message to the job log and print it."""
    JOBS[job_id]["logs"].append(msg)
    logger.info(f"[{job_id}] {msg}")


def _run_job(
    job_id: str,
    input_path: Path,
    job_dir: Path,
    clip_length: int,
    num_clips: int,
    subtitle_pos: str,
    model: str,
    lang: str,
) -> None:
    """Full clippr pipeline for one job, runs in a background thread."""
    job = JOBS[job_id]

    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))

        from tracker         import track_speaker
        from smoother        import smooth_boxes
        from transcriber     import group_into_segments
        from caption_builder import build_ass
        from video_processor import process_video, _probe_video
        from analyzer        import analyze_video, words_for_segment
        from segment_registry import register_segments, get_used_summary

        # ── Probe video ─────────────────────────────────────────────
        _log(job_id, f"Probing input: {input_path.name}")
        vid_w, vid_h, fps = _probe_video(str(input_path))
        total_duration    = _get_duration(str(input_path))
        _log(job_id, f"Video: {vid_w}×{vid_h} @ {fps:.2f}fps, duration={total_duration:.1f}s")

        margin = min(5.0, total_duration * 0.05)

        # ── Registry: show already-used segments ────────────────────
        summary = get_used_summary(str(input_path))
        used_segs = summary.get("segments", [])
        if summary["used_count"] > 0:
            _log(job_id,
                 f"Registry: {summary['used_count']} segments already used "
                 f"({summary['used_seconds']}s / {total_duration:.1f}s total). "
                 f"Picking only unused parts.")

        # ── Stage 1: Transcribe FULL video once ─────────────────────
        job["stage"]    = "transcribing"
        job["progress"] = 5
        _log(job_id, f"Transcribing full video with Whisper ({model})…")

        clip_starts, all_words, scenes = analyze_video(
            str(input_path),
            model_size=model,
            language=lang,
            clip_length=clip_length,
            num_clips=num_clips,
            margin=margin,
            already_used=used_segs,
        )

        if not clip_starts:
            raise RuntimeError(
                f"No unused segments left in '{input_path.name}'. "
                "All distinct parts have already been processed. "
                "Upload a different video or reset the history."
            )

        num_clips = len(clip_starts)
        _log(job_id,
             f"Found {len(scenes)} speech scenes → selected {num_clips} clips:")
        for i, s in enumerate(clip_starts):
            _log(job_id, f"  clip {i+1}: {s:.1f}s → {s+clip_length:.1f}s")

        # ── Per-clip rendering ───────────────────────────────────────
        target_h     = int(1080 * 16 / 9)
        v_margin_pct = 0.10 if subtitle_pos == "bottom" else 0.45
        v_margin     = int(target_h * v_margin_pct)
        all_clips_meta = []

        for clip_idx in range(num_clips):
            clip_label = f"clip {clip_idx + 1}/{num_clips}"
            start_time = clip_starts[clip_idx]
            end_time   = min(start_time + clip_length, total_duration)
            actual_len = end_time - start_time

            _log(job_id, f"── {clip_label} | {start_time:.1f}s → {end_time:.1f}s ──")

            # Extract segment
            job["stage"]    = "tracking"
            job["progress"] = _clip_progress(clip_idx, num_clips, 0)
            segment_path    = job_dir / f"segment_{clip_idx:02d}.mp4"
            _log(job_id, f"[{clip_label}] Extracting segment…")
            _extract_segment(str(input_path), str(segment_path), start_time, actual_len)

            # Track speaker
            _log(job_id, f"[{clip_label}] Tracking speaker (YOLOv8)…")
            raw_boxes = track_speaker(str(segment_path), sample_every_n=3)
            job["progress"] = _clip_progress(clip_idx, num_clips, 25)

            # Smooth
            job["stage"]    = "smoothing"
            job["progress"] = _clip_progress(clip_idx, num_clips, 35)
            _log(job_id, f"[{clip_label}] Smoothing…")
            smoothed = smooth_boxes(raw_boxes)

            # Slice words for this segment from the full transcript
            job["stage"]    = "captions"
            job["progress"] = _clip_progress(clip_idx, num_clips, 50)
            clip_words = words_for_segment(all_words, start_time, end_time)
            clip_segs  = group_into_segments(clip_words)
            _log(job_id, f"[{clip_label}] {len(clip_words)} words → {len(clip_segs)} caption segments")

            # Build ASS
            ass_path = job_dir / f"captions_{clip_idx:02d}.ass"
            _log(job_id, f"[{clip_label}] Building captions ({subtitle_pos})…")
            _build_ass_with_margin(clip_segs, str(ass_path), 1080, target_h, v_margin)

            # Render
            job["stage"]    = "rendering"
            job["progress"] = _clip_progress(clip_idx, num_clips, 65)
            output_path     = job_dir / f"clip_{clip_idx + 1:02d}.mp4"
            _log(job_id, f"[{clip_label}] Rendering 9:16 clip…")
            process_video(
                input_path=str(segment_path),
                smoothed_boxes=smoothed,
                ass_path=str(ass_path),
                output_path=str(output_path),
                target_width=1080,
                words=clip_words,
                subtitle_pos=subtitle_pos,
            )
            _log(job_id, f"[{clip_label}] ✓ Saved: {output_path.name}")
            job["progress"] = _clip_progress(clip_idx + 1, num_clips, 0)

            all_clips_meta.append({
                "filename": output_path.name,
                "duration": _fmt_dur(actual_len),
                "index":    clip_idx + 1,
            })

            # Clean up temp files
            try:
                segment_path.unlink()
                ass_path.unlink()
            except Exception:
                pass

        # ── Persist used segments ────────────────────────────────────
        register_segments(str(input_path), total_duration, clip_starts, clip_length, job_id)

        # ── Done ────────────────────────────────────────────────────
        job["stage"]    = "done"
        job["progress"] = 100
        job["status"]   = "done"
        job["clips"]    = all_clips_meta
        _log(job_id, f"✓ All {num_clips} clips complete!")

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[{job_id}] Job failed:\n{tb}")
        job["status"] = "error"
        job["error"]  = str(exc)
        _log(job_id, f"ERROR: {exc}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clip_progress(clip_idx: int, total: int, within_pct: float) -> float:
    """Map per-clip progress to an overall 0–100 value."""
    per_clip = 100.0 / total
    return clip_idx * per_clip + within_pct * per_clip / 100.0


def _ffmpeg_bin() -> str:
    import shutil
    from pathlib import Path as _P
    full = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    return full if _P(full).exists() else (shutil.which("ffmpeg") or "ffmpeg")


def _ffprobe_bin() -> str:
    import shutil
    from pathlib import Path as _P
    full = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
    return full if _P(full).exists() else (shutil.which("ffprobe") or "ffprobe")


def _extract_segment(src: str, dst: str, start: float, duration: float) -> None:
    cmd = [
        _ffmpeg_bin(), "-y",
        "-ss", str(start),
        "-i", src,
        "-t", str(duration),
        "-c", "copy",
        dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Segment extraction failed: {r.stderr[-500:]}")


def _get_duration(path: str) -> float:
    cmd = [
        _ffprobe_bin(), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _fmt_dur(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def _build_ass_with_margin(segments, out_path, w, h, v_margin):
    """Wrapper around caption_builder.build_ass with custom vertical margin."""
    from caption_builder import _ass_header, _build_karaoke_line
    from pathlib import Path as P

    lines = []
    lines.append(_ass_header_custom(w, h, 65, v_margin))
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for segment in segments:
        if not segment:
            continue
        seg_start = segment[0]["start"]
        seg_end   = segment[-1]["end"]
        dialogue  = _build_karaoke_line(segment, seg_start, seg_end)
        lines.append(dialogue)

    P(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ass_header_custom(width, height, font_size, v_margin):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,3,2,30,30,{v_margin},1"""


def _detect_speakers(words: list, total_duration: float) -> list:
    """
    Simple pause-based speaker diarization.
    Finds speech blocks separated by >= 1.5s pauses and groups them
    into 'speakers' based on their sequence in the video.
    Groups consecutive blocks belonging to the same voice period.
    Returns list of speaker dicts sorted by speaking time descending.
    """
    if not words:
        return []

    # Split into blocks at pauses >= 1.2s
    blocks = []
    current = [words[0]]
    for prev, curr in zip(words, words[1:]):
        if curr["start"] - prev["end"] >= 1.2:
            blocks.append(current)
            current = [curr]
        else:
            current.append(curr)
    if current:
        blocks.append(current)

    # Simple heuristic: alternate speakers at long pauses > 2.5s
    # (or keep as single speaker if video is short)
    speakers_raw = {}
    current_speaker = 1
    last_block_end = 0

    for block in blocks:
        block_start = block[0]["start"]
        block_end   = block[-1]["end"]
        gap_before  = block_start - last_block_end

        # Long gap → likely a different speaker takes the floor
        if gap_before >= 2.5 and last_block_end > 0:
            current_speaker = (current_speaker % 5) + 1  # cycle 1-5

        spk = f"Speaker {current_speaker}"
        if spk not in speakers_raw:
            speakers_raw[spk] = {"words": [], "duration": 0.0, "preview": ""}
        speakers_raw[spk]["words"].extend(block)
        speakers_raw[spk]["duration"] += block_end - block_start
        last_block_end = block_end

    # Build output list
    result = []
    for idx, (name, data) in enumerate(speakers_raw.items(), 1):
        w = data["words"]
        preview_text = " ".join(x["word"] for x in w[:12])
        result.append({
            "id":           idx,
            "name":         name,
            "word_count":   len(w),
            "duration":     round(data["duration"], 1),
            "duration_fmt": _fmt_dur(data["duration"]),
            "preview":      f"\"{preview_text}…\"",
        })

    # Sort by duration descending
    result.sort(key=lambda s: s["duration"], reverse=True)
    for i, s in enumerate(result):
        s["id"] = i + 1
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Install flask if missing
    try:
        import flask
    except ImportError:
        import subprocess as sp
        sp.run(["pip", "install", "flask"], check=True)
        import flask  # noqa

    print("\n" + "="*56)
    print("  clippr web server")
    print("  Open: http://localhost:5050")
    print("="*56 + "\n")

    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
