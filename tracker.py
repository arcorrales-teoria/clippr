"""
tracker.py — YOLOv8 + ByteTrack person detection and tracking.
Returns per-frame bounding boxes for the primary speaker.
"""

import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def track_speaker(video_path: str, sample_every_n: int = 3) -> dict:
    """
    Run YOLOv8 detection on the input video.

    Returns:
        dict mapping frame_index -> (x_center, y_center, box_width, box_height)
        coordinates are in pixels relative to the original video dimensions.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError("ultralytics not installed. Run: pip install ultralytics")

    logger.info("Loading YOLOv8 model (yolov8n.pt)...")
    model = YOLO("yolov8n.pt")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    logger.info(
        f"Video: {total_frames} frames, {fps:.2f} fps, {width}x{height}"
    )

    raw_boxes: dict = {}
    last_known: tuple | None = None
    no_detect_count = 0
    no_detect_limit = int(fps * 5)  # 5 seconds of no detection triggers fallback

    frame_idx = 0
    sampled_frames = {}

    logger.info(f"Detecting persons (sampling every {sample_every_n} frames)...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every_n == 0:
            # Run inference on this frame — only class 0 (person)
            results = model(frame, classes=[0], verbose=False)

            best_box = _pick_best_box(results, width, height)

            if best_box is not None:
                sampled_frames[frame_idx] = best_box
                last_known = best_box
                no_detect_count = 0
            else:
                no_detect_count += sample_every_n
                if no_detect_count >= no_detect_limit or last_known is None:
                    # Fallback: center of frame
                    sampled_frames[frame_idx] = (
                        width // 2,
                        height // 2,
                        width // 2,
                        height // 2,
                    )
                else:
                    sampled_frames[frame_idx] = last_known

            if frame_idx % 100 == 0:
                pct = frame_idx / max(total_frames, 1) * 100
                logger.info(f"  Tracking progress: {pct:.1f}%")

        frame_idx += 1

    cap.release()

    # Interpolate between sampled frames to get every frame
    logger.info("Interpolating bounding boxes for all frames...")
    raw_boxes = _interpolate_boxes(sampled_frames, total_frames, sample_every_n)

    logger.info(f"Tracking complete. Processed {len(raw_boxes)} frames.")
    return raw_boxes


def _pick_best_box(results, frame_width: int, frame_height: int) -> tuple | None:
    """Select the highest-confidence person bounding box from YOLO results."""
    best_conf = -1.0
    best_box = None

    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cls = int(box.cls[0])
            if cls != 0:
                continue
            conf = float(box.conf[0])
            if conf > best_conf:
                best_conf = conf
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = xyxy
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                bw = x2 - x1
                bh = y2 - y1
                best_box = (cx, cy, bw, bh)

    return best_box


def _interpolate_boxes(
    sampled: dict, total_frames: int, step: int
) -> dict:
    """Linear interpolation between sampled keyframes."""
    if not sampled:
        return {}

    all_boxes = {}
    sorted_keys = sorted(sampled.keys())

    # Fill before first sample
    first_key = sorted_keys[0]
    for i in range(first_key):
        all_boxes[i] = sampled[first_key]

    # Interpolate between keyframes
    for i in range(len(sorted_keys) - 1):
        k0 = sorted_keys[i]
        k1 = sorted_keys[i + 1]
        b0 = sampled[k0]
        b1 = sampled[k1]
        span = k1 - k0
        for f in range(k0, k1):
            t = (f - k0) / max(span, 1)
            interp = tuple(b0[j] + t * (b1[j] - b0[j]) for j in range(4))
            all_boxes[f] = interp

    # Fill after last sample
    last_key = sorted_keys[-1]
    for i in range(last_key, total_frames):
        all_boxes[i] = sampled[last_key]

    return all_boxes
