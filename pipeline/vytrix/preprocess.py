"""Stage 1: Frame extraction and blur filtering for smartphone video captures."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def compute_blur_score(frame: np.ndarray) -> float:
    """Compute the Laplacian variance score of an image to quantify sharpness.

    Higher scores indicate sharper details; lower scores indicate motion blur or out-of-focus capture.

    Args:
        frame: BGR image array.

    Returns:
        Laplacian variance score as float.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def extract_frames(
    video_path: str | Path,
    output_dir: str | Path,
    target_frames: int = 350,
    blur_threshold: float = 100.0,
    downscale_factor: int = 1,
) -> dict[str, Any]:
    """Extract, filter, and save sharp frames from an input video file.

    Args:
        video_path: Path to the smartphone MP4 video file.
        output_dir: Directory where extracted sharp frames and manifest will be stored.
        target_frames: Target number of frames to sample across the video.
        blur_threshold: Minimum Laplacian variance score required to keep a frame.
        downscale_factor: Downscale multiplier (1 = full size, 2 = half resolution).

    Returns:
        Dictionary summarizing extraction metrics and frame counts.
    """
    v_path = Path(video_path)
    out_dir = Path(output_dir)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found at: {v_path.resolve()}")

    cap = cv2.VideoCapture(str(v_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {v_path.resolve()}")

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculate step interval to evenly sample target_frames
    interval = max(1, total_video_frames // target_frames)
    logger.info(
        "Video metadata: %d frames, %.1f FPS, %dx%d. Sampling interval: %d",
        total_video_frames,
        fps,
        width,
        height,
        interval,
    )

    start_time = time.time()
    frame_idx = 0
    saved_count = 0
    rejected_count = 0
    frame_scores: list[tuple[str, float]] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval == 0:
            if downscale_factor > 1:
                new_w = width // downscale_factor
                new_h = height // downscale_factor
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            score = compute_blur_score(frame)
            if score >= blur_threshold:
                saved_count += 1
                filename = f"frame_{saved_count:05d}.jpg"
                save_path = frames_dir / filename
                cv2.imwrite(str(save_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                frame_scores.append((filename, score))
            else:
                rejected_count += 1

        frame_idx += 1

    cap.release()
    elapsed = time.time() - start_time

    avg_sharpness = float(np.mean([s[1] for s in frame_scores])) if frame_scores else 0.0

    manifest = {
        "stage": "preprocess",
        "video_file": str(v_path.name),
        "total_video_frames": total_video_frames,
        "sampled_frames": saved_count + rejected_count,
        "saved_sharp_frames": saved_count,
        "rejected_blurry_frames": rejected_count,
        "blur_threshold": blur_threshold,
        "average_sharpness_score": round(avg_sharpness, 2),
        "elapsed_seconds": round(elapsed, 2),
        "output_directory": str(frames_dir.resolve()),
    }

    manifest_path = out_dir / "preprocess_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "Preprocessing complete: %d sharp frames saved, %d blurry rejected in %.2fs",
        saved_count,
        rejected_count,
        elapsed,
    )
    return manifest
