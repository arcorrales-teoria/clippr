"""
smoother.py — Smooths per-frame bounding box coordinates to eliminate jitter.
Uses a combination of rolling average and exponential smoothing.
"""

import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


def smooth_boxes(
    raw_boxes: dict,
    window: int = 30,
    alpha: float = 0.05,
) -> dict:
    """
    Smooth the x_center and y_center from raw_boxes to reduce camera jitter.

    Args:
        raw_boxes: {frame_index: (x_center, y_center, width, height)}
        window:    Rolling average window size in frames
        alpha:     Exponential smoothing factor (lower = smoother but laggier)

    Returns:
        Smoothed dict in the same format.
    """
    if not raw_boxes:
        return {}

    logger.info(f"Smoothing bounding boxes (window={window}, alpha={alpha})...")

    sorted_keys = sorted(raw_boxes.keys())
    n = len(sorted_keys)

    xs = np.array([raw_boxes[k][0] for k in sorted_keys], dtype=float)
    ys = np.array([raw_boxes[k][1] for k in sorted_keys], dtype=float)
    ws = np.array([raw_boxes[k][2] for k in sorted_keys], dtype=float)
    hs = np.array([raw_boxes[k][3] for k in sorted_keys], dtype=float)

    # Step 1: Rolling average
    xs_roll = _rolling_mean(xs, window)
    ys_roll = _rolling_mean(ys, window)

    # Step 2: Exponential smoothing on top
    xs_smooth = _exp_smooth(xs_roll, alpha)
    ys_smooth = _exp_smooth(ys_roll, alpha)

    smoothed = {}
    for i, k in enumerate(sorted_keys):
        smoothed[k] = (
            float(xs_smooth[i]),
            float(ys_smooth[i]),
            float(ws[i]),
            float(hs[i]),
        )

    logger.info("Smoothing complete.")
    return smoothed


def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    """Compute a centered rolling mean with edge padding."""
    half = window // 2
    padded = np.pad(arr, (half, half), mode="edge")
    kernel = np.ones(window) / window
    smoothed = np.convolve(padded, kernel, mode="valid")
    # Trim to original length
    return smoothed[: len(arr)]


def _exp_smooth(arr: np.ndarray, alpha: float) -> np.ndarray:
    """One-pass exponential smoothing."""
    result = np.empty_like(arr)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return result
