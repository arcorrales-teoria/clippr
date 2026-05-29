"""
video_processor.py — FFmpeg pipeline: dynamic crop → scale → subtitle burn → export.

Subtitle strategy (auto-detected at runtime):
  1. ffmpeg-full  → uses `ass=f=` filter   (full karaoke styling via libass)
  2. standard ffmpeg → uses `drawtext` filter chain (per-word highlight, no libass needed)
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Prefer ffmpeg-full (has libass + drawtext) over the standard minimal build
_FFMPEG_FULL = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
_FFPROBE_FULL = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"

def _ffmpeg_bin() -> str:
    if Path(_FFMPEG_FULL).exists():
        return _FFMPEG_FULL
    return shutil.which("ffmpeg") or "ffmpeg"

def _ffprobe_bin() -> str:
    if Path(_FFPROBE_FULL).exists():
        return _FFPROBE_FULL
    return shutil.which("ffprobe") or "ffprobe"

# Cache the libass availability check so we only probe once per process
_HAS_LIBASS: bool | None = None


def process_video(
    input_path: str,
    smoothed_boxes: dict,
    ass_path: str,
    output_path: str,
    target_width: int = 1080,
    fps: float | None = None,
    words: list | None = None,       # word-level timestamps for drawtext fallback
    subtitle_pos: str = "bottom",    # "bottom" or "middle"
) -> str:
    """
    Run the full FFmpeg pipeline.

    Args:
        input_path:    Source video file path
        smoothed_boxes: {frame_index: (x_center, y_center, box_w, box_h)}
        ass_path:      Path to the .ass subtitle file (used when libass available)
        output_path:   Destination MP4 path
        target_width:  Output width in pixels (height = width * 16/9)
        fps:           Original video FPS (auto-detected if None)
        words:         Word-level timestamps for drawtext fallback
        subtitle_pos:  "bottom" or "middle"

    Returns:
        Path to the output file.
    """
    input_path  = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vid_w, vid_h, vid_fps = _probe_video(str(input_path))
    if fps is None:
        fps = vid_fps

    target_height = int(target_width * 16 / 9)
    target_width  = target_width  if target_width  % 2 == 0 else target_width  + 1
    target_height = target_height if target_height % 2 == 0 else target_height + 1

    logger.info(
        f"Input: {vid_w}x{vid_h} @ {vid_fps:.2f}fps → Output: {target_width}x{target_height}"
    )

    crop_rects   = _compute_crop_rects(smoothed_boxes, vid_w, vid_h, target_width, target_height)
    sendcmd_path = _write_sendcmd(crop_rects, fps)
    log_path     = output_path.parent / "ffmpeg.log"

    use_libass = _check_libass()
    if use_libass:
        logger.info("Subtitle engine: libass (ass filter)")
        subtitle_filter = f"ass=f='{_escape_ffmpeg_path(ass_path)}'"
    else:
        logger.info("Subtitle engine: drawtext fallback (libass not in this ffmpeg build)")
        subtitle_filter = _build_drawtext_filter(
            words or [], target_width, target_height, subtitle_pos
        )

    _run_ffmpeg(
        str(input_path),
        sendcmd_path,
        subtitle_filter,
        str(output_path),
        target_width,
        target_height,
        vid_w,
        vid_h,
        str(log_path),
    )

    try:
        Path(sendcmd_path).unlink()
    except Exception:
        pass

    logger.info(f"Output saved: {output_path}")
    return str(output_path)


# ── libass detection ──────────────────────────────────────────────────────────

def _check_libass() -> bool:
    global _HAS_LIBASS
    if _HAS_LIBASS is not None:
        return _HAS_LIBASS

    # Try a zero-length test encode with the ass filter
    result = subprocess.run(
        [_ffmpeg_bin(), "-f", "lavfi", "-i", "color=c=black:s=16x16:d=0.1",
         "-vf", "ass=f=/dev/null", "-t", "0.1", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # If it fails with "No such filter" → no libass; any other error means libass IS there
    # (the /dev/null file not found is fine — the filter was recognised)
    _HAS_LIBASS = "No such filter" not in result.stderr
    logger.info(f"libass available: {_HAS_LIBASS}")
    return _HAS_LIBASS


# ── Drawtext caption fallback ─────────────────────────────────────────────────

def _build_drawtext_filter(
    words: list,
    out_w: int,
    out_h: int,
    subtitle_pos: str = "bottom",
) -> str:
    """
    Build an FFmpeg drawtext filter chain that shows each word highlighted as it
    is spoken — karaoke style — without needing libass.

    Strategy:
      • For each caption SEGMENT (up to 5 words), show the full segment in white
        for its duration.
      • On top of that, show each individual word in yellow for its exact duration.
      • Both layers use drawtext with enable='between(t,start,end)'.
    """
    if not words:
        return "null"   # passthrough — no captions

    font_size   = max(42, int(out_w * 0.052))   # ~56px at 1080
    y_expr      = f"h*0.85" if subtitle_pos == "bottom" else f"h*0.45"
    margin_y    = int(out_h * (0.10 if subtitle_pos == "bottom" else 0.45))

    # Group words into segments (max 5 words / 2.5s)
    segments = _group_words(words, max_words=5, max_dur=2.5)
    filters  = []

    def _esc(text: str) -> str:
        """Escape text for FFmpeg drawtext."""
        return (text
                .replace("\\", "\\\\")
                .replace("'",  "\\'")
                .replace(":",  "\\:")
                .replace("%",  "\\%"))

    for seg in segments:
        if not seg:
            continue
        seg_start = seg[0]["start"]
        seg_end   = seg[-1]["end"]
        seg_text  = " ".join(w["word"] for w in seg)

        # Full segment in white (background text)
        filters.append(
            f"drawtext=text='{_esc(seg_text)}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":bordercolor=black:borderw=4"
            f":x=(w-text_w)/2:y={y_expr}"
            f":enable='between(t,{seg_start:.3f},{seg_end:.3f})'"
        )

        # Each word highlighted in yellow when active
        for w in seg:
            filters.append(
                f"drawtext=text='{_esc(w['word'])}'"
                f":fontsize={font_size}"
                f":fontcolor=yellow"
                f":bordercolor=black:borderw=4"
                f":x=(w-text_w)/2:y={y_expr}"
                f":enable='between(t,{w['start']:.3f},{w['end']:.3f})'"
            )

    return ",".join(filters) if filters else "null"


def _group_words(words: list, max_words: int = 5, max_dur: float = 2.5) -> list:
    segments, current = [], []
    for w in words:
        if not current:
            current.append(w)
            continue
        if len(current) >= max_words or (w["end"] - current[0]["start"]) > max_dur:
            segments.append(current)
            current = [w]
        else:
            current.append(w)
    if current:
        segments.append(current)
    return segments


# ── Crop computation ──────────────────────────────────────────────────────────

def _compute_crop_rects(
    boxes: dict,
    vid_w: int,
    vid_h: int,
    out_w: int,
    out_h: int,
) -> dict:
    aspect_in = vid_w / vid_h

    if aspect_in >= 1.0:
        # Landscape: fix height, pan horizontally
        crop_h = vid_h
        crop_w = int(vid_h * (out_w / out_h))
        crop_w = min(crop_w, vid_w)
        crop_w = crop_w if crop_w % 2 == 0 else crop_w - 1
        crop_h = crop_h if crop_h % 2 == 0 else crop_h - 1

        rects = {}
        for frame_idx, (cx, cy, bw, bh) in boxes.items():
            x = int(cx - crop_w / 2)
            x = max(0, min(x, vid_w - crop_w))
            x = x if x % 2 == 0 else x + 1
            rects[frame_idx] = (x, 0, crop_w, crop_h)
    else:
        # Portrait: fix width, pan vertically
        crop_w = vid_w
        crop_h = int(vid_w * (out_h / out_w))
        crop_h = min(crop_h, vid_h)
        crop_w = crop_w if crop_w % 2 == 0 else crop_w - 1
        crop_h = crop_h if crop_h % 2 == 0 else crop_h - 1

        rects = {}
        for frame_idx, (cx, cy, bw, bh) in boxes.items():
            y = int(cy - crop_h / 2)
            y = max(0, min(y, vid_h - crop_h))
            y = y if y % 2 == 0 else y + 1
            rects[frame_idx] = (0, y, crop_w, crop_h)

    return rects


# ── sendcmd file ──────────────────────────────────────────────────────────────

def _write_sendcmd(crop_rects: dict, fps: float) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    sorted_frames = sorted(crop_rects.keys())
    prev_rect = None
    for frame_idx in sorted_frames:
        rect = crop_rects[frame_idx]
        if rect == prev_rect:
            continue
        prev_rect = rect
        t = frame_idx / fps
        x, y, w, h = rect
        tmp.write(f"{t:.6f} crop x {x};\n")
        tmp.write(f"{t:.6f} crop y {y};\n")
        tmp.write(f"{t:.6f} crop w {w};\n")
        tmp.write(f"{t:.6f} crop h {h};\n")
    tmp.close()
    return tmp.name


# ── FFmpeg execution ──────────────────────────────────────────────────────────

def _run_ffmpeg(
    input_path: str,
    sendcmd_path: str,
    subtitle_filter: str,
    output_path: str,
    out_w: int,
    out_h: int,
    vid_w: int,
    vid_h: int,
    log_path: str,
) -> None:
    init_w = int(vid_h * out_w / out_h)
    init_w = min(init_w, vid_w)
    init_w = init_w if init_w % 2 == 0 else init_w - 1
    init_h = vid_h if vid_h % 2 == 0 else vid_h - 1
    init_x = max(0, (vid_w - init_w) // 2)
    init_y = 0

    sendcmd_escaped = _escape_ffmpeg_path(sendcmd_path)

    filter_graph = (
        f"sendcmd=f='{sendcmd_escaped}',"
        f"crop={init_w}:{init_h}:{init_x}:{init_y},"
        f"scale={out_w}:{out_h}:flags=lanczos,"
        f"{subtitle_filter}"
    )

    cmd = [
        _ffmpeg_bin(), "-y",
        "-i", input_path,
        "-vf", filter_graph,
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info(f"Running FFmpeg ({_ffmpeg_bin()})...")

    with open(log_path, "w") as log_file:
        result = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, text=True)

    if result.returncode != 0:
        try:
            tail = Path(log_path).read_text(encoding="utf-8").splitlines()[-40:]
            logger.error("FFmpeg failed:\n" + "\n".join(tail))
        except Exception:
            pass
        raise RuntimeError(
            f"FFmpeg exited with code {result.returncode}. Full log: {log_path}"
        )


def _escape_ffmpeg_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


# ── Video probe ───────────────────────────────────────────────────────────────

def _probe_video(path: str) -> tuple[int, int, float]:
    cmd = [
        _ffprobe_bin(), "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    parts   = result.stdout.strip().split(",")
    width   = int(parts[0])
    height  = int(parts[1])
    fps_str = parts[2]
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)

    return width, height, fps
