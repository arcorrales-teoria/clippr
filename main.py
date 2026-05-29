#!/usr/bin/env python3
"""
clippr — Local CLI tool for auto-tracking speaker clips with karaoke captions.

Usage:
    python main.py --input video.mp4
    python main.py --input video.mp4 --output out.mp4 --model small --lang es
"""

import argparse
import logging
import sys
from pathlib import Path


# ── Logging setup ─────────────────────────────────────────────────────────────

def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


# ── Dependency checks ─────────────────────────────────────────────────────────

def _check_ffmpeg() -> None:
    import subprocess
    result = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(
            "\n[ERROR] FFmpeg not found.\n"
            "  macOS:  brew install ffmpeg\n"
            "  Linux:  sudo apt install ffmpeg -y\n"
        )
        sys.exit(1)


def _preload_models(model_size: str) -> None:
    """Download / verify model weights are present."""
    log = logging.getLogger(__name__)

    log.info("Checking YOLOv8 weights...")
    try:
        from ultralytics import YOLO
        YOLO("yolov8n.pt")  # Downloads on first run
    except Exception as e:
        log.error(f"Failed to load YOLOv8: {e}")
        sys.exit(1)

    log.info(f"Checking Whisper model ({model_size})...")
    try:
        import whisper
        whisper.load_model(model_size)
    except Exception as e:
        log.error(f"Failed to load Whisper: {e}")
        sys.exit(1)

    log.info("All models ready.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clippr",
        description="Auto-track speaker + karaoke captions → 9:16 vertical clip.",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input video file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help=(
            "Path to output MP4. "
            "Default: ~/Desktop/clippr/outputs/<name>_clip.mp4"
        ),
    )
    parser.add_argument(
        "--model", "-m",
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--lang", "-l",
        default="es",
        help="Language hint for Whisper (default: es)",
    )
    parser.add_argument(
        "--caption-style",
        default="karaoke",
        choices=["karaoke"],
        help="Caption animation style (default: karaoke)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1080,
        help="Output width in pixels — height auto-set to 16/9 ratio (default: 1080)",
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=3,
        help="YOLO sample rate: process 1 of every N frames (default: 3)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--skip-preload",
        action="store_true",
        help="Skip model preload check (faster if models already downloaded)",
    )
    return parser.parse_args()


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    # ── Validate input ─────────────────────────────────────────────────────────
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        log.error(f"Input file not found: {input_path}")
        sys.exit(1)

    # ── Resolve output path ────────────────────────────────────────────────────
    clippr_root = Path("~/Desktop/clippr").expanduser()
    outputs_dir = clippr_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        stem = input_path.stem
        output_path = outputs_dir / f"{stem}_clip.mp4"

    ass_path   = outputs_dir / f"{input_path.stem}.ass"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("  clippr — local speaker-tracking clip generator")
    log.info("=" * 60)
    log.info(f"  Input  : {input_path}")
    log.info(f"  Output : {output_path}")
    log.info(f"  Model  : Whisper {args.model}  |  Lang: {args.lang}")
    log.info(f"  Size   : {args.max_width}px wide  ({args.max_width}x{int(args.max_width*16/9)})")
    log.info("=" * 60)

    # ── Checks ─────────────────────────────────────────────────────────────────
    _check_ffmpeg()
    if not args.skip_preload:
        _preload_models(args.model)

    # ── Stage 1: Person detection & tracking ───────────────────────────────────
    log.info("\n[1/5] Tracking speaker...")
    from tracker import track_speaker
    raw_boxes = track_speaker(str(input_path), sample_every_n=args.sample_every)

    # ── Stage 2: Smooth bounding boxes ────────────────────────────────────────
    log.info("\n[2/5] Smoothing bounding boxes...")
    from smoother import smooth_boxes
    smoothed_boxes = smooth_boxes(raw_boxes)

    # ── Stage 3: Transcribe audio ─────────────────────────────────────────────
    log.info("\n[3/5] Transcribing audio...")
    from transcriber import transcribe, group_into_segments
    words = transcribe(str(input_path), model_size=args.model, language=args.lang)

    if not words:
        log.warning("No speech detected — captions will be empty.")

    segments = group_into_segments(words)
    log.info(f"  {len(words)} words → {len(segments)} caption segments")

    # ── Stage 4: Build .ASS subtitle file ─────────────────────────────────────
    log.info("\n[4/5] Building caption file...")
    from caption_builder import build_ass
    target_height = int(args.max_width * 16 / 9)
    build_ass(
        segments,
        output_path=str(ass_path),
        video_width=args.max_width,
        video_height=target_height,
    )

    # ── Stage 5: Render final video ────────────────────────────────────────────
    log.info("\n[5/5] Rendering video (this may take a while)...")
    from video_processor import process_video
    result = process_video(
        input_path=str(input_path),
        smoothed_boxes=smoothed_boxes,
        ass_path=str(ass_path),
        output_path=str(output_path),
        target_width=args.max_width,
    )

    log.info("\n" + "=" * 60)
    log.info("  Done!")
    log.info(f"  Output file: {result}")
    log.info("=" * 60)
    print(f"\nOutput saved to: {result}\n")


if __name__ == "__main__":
    main()
