"""Stage 2: Structure-from-Motion (SfM) camera pose estimation using COLMAP."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_model_analyzer_output(output_text: str) -> dict[str, Any]:
    """Parse output from `colmap model_analyzer` (stdout + stderr).

    Expected COLMAP format:
    ----------------------------------------------------------------
    Model statistics:
    ----------------------------------------------------------------
    Cameras: 1
    Images: 247
    Registered images: 243
    Points: 45892
    Mean track length: 4.312
    Mean observations per image: 802.45
    Mean reprojection error: 0.723 px (or 0.723px)
    ----------------------------------------------------------------

    Args:
        output_text: Combined stdout and stderr text from colmap model_analyzer.

    Returns:
        Dictionary with parsed integer/float fields.

    Raises:
        ValueError: If required fields cannot be found in the output.
    """
    reg_img_match = re.search(r"Registered images:\s*([0-9,]+)", output_text, re.IGNORECASE)
    images_match = re.search(r"(?<!Registered\s)Images:\s*([0-9,]+)", output_text, re.IGNORECASE)
    points_match = re.search(r"Points:\s*([0-9,]+)", output_text, re.IGNORECASE)
    reproj_match = re.search(r"Mean reprojection error:\s*([0-9.]+)\s*(?:px)?", output_text, re.IGNORECASE)

    if not reg_img_match or not images_match:
        raise ValueError(
            "Failed to parse COLMAP model_analyzer output. Output did not contain image counts:\n"
            f"{output_text}"
        )

    registered_images = int(reg_img_match.group(1).replace(",", ""))
    total_images = int(images_match.group(1).replace(",", ""))
    points = int(points_match.group(1).replace(",", "")) if points_match else 0
    mean_reproj_error_px = float(reproj_match.group(1)) if reproj_match else None

    return {
        "total_images": total_images,
        "registered_images": registered_images,
        "points_count": points,
        "mean_reprojection_error_px": mean_reproj_error_px,
    }


def select_best_sparse_model(sparse_root: Path) -> Path:
    """Find and select the COLMAP sub-model with the most registered images or largest size.

    COLMAP mapper outputs sub-models into `sparse/0`, `sparse/1`, etc. If only one model was
    reconstructed directly in `sparse_root`, returns that directory.

    Args:
        sparse_root: Root directory where mapper saved models.

    Returns:
        Path to the best sub-model directory containing cameras, images, points3D files.

    Raises:
        FileNotFoundError: If no valid COLMAP reconstruction model is found.
    """
    subdirs = [p for p in sparse_root.iterdir() if p.is_dir() and p.name.isdigit()]
    if not subdirs:
        # Check if cameras/images/points3D exist directly in sparse_root
        has_bin = (sparse_root / "cameras.bin").exists() or (sparse_root / "cameras.txt").exists()
        if has_bin:
            return sparse_root
        raise FileNotFoundError(
            f"No COLMAP models found in {sparse_root}. Mapping stage failed to register any images."
        )

    # Sort subdirs by number of registered images in images.bin or images.txt
    best_dir = subdirs[0]
    best_count = -1

    for s_dir in subdirs:
        count = 0
        img_bin = s_dir / "images.bin"
        img_txt = s_dir / "images.txt"
        if img_bin.exists():
            # Rough estimate from file size
            count = img_bin.stat().st_size
        elif img_txt.exists():
            with open(img_txt, "r", encoding="utf-8", errors="ignore") as f:
                # In images.txt, non-comment odd lines contain image names
                count = sum(1 for line in f if not line.startswith("#") and line.strip()) // 2

        if count > best_count:
            best_count = count
            best_dir = s_dir

    logger.info("Selected COLMAP sub-model %s (score: %d)", best_dir.name, best_count)
    return best_dir


def run_colmap_sfm(
    images_dir: str | Path,
    output_dir: str | Path,
    camera_model: str = "SIMPLE_RADIAL",
    matcher: str = "auto",
    matcher_auto_threshold: int = 300,
    overlap_window: int = 20,
    loop_detection: bool = True,
    min_registered_ratio: float = 0.70,
    use_gpu: bool = True,
) -> dict[str, Any]:
    """Execute COLMAP feature extraction, matching, and sparse reconstruction.

    Args:
        images_dir: Directory containing extracted sharp JPEG frames.
        output_dir: Directory to store COLMAP database and sparse reconstruction models.
        camera_model: COLMAP camera model (e.g. SIMPLE_RADIAL, OPENCV).
        matcher: "auto" (exhaustive if <= matcher_auto_threshold else sequential), "exhaustive", or "sequential".
        matcher_auto_threshold: Frame threshold below which exhaustive matching is chosen.
        overlap_window: Number of consecutive frames matched in sequential matcher.
        loop_detection: Whether to enable loop closure detection in sequential matcher.
        min_registered_ratio: Minimum ratio of registered images vs total images.
        use_gpu: Whether to request GPU SIFT extraction and matching.

    Returns:
        Dict containing real parsed camera pose counts and reprojection metrics.

    Raises:
        RuntimeError: If any COLMAP stage fails or registration ratio is below threshold.
    """
    img_path = Path(images_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    database_path = out_path / "database.db"
    sparse_dir = out_path / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    total_images = len(list(img_path.glob("*.jpg"))) + len(list(img_path.glob("*.png")))
    if total_images == 0:
        raise RuntimeError(f"No image frames found in {img_path}")

    start_time = time.time()
    logger.info("Starting COLMAP SfM for %d images in %s", total_images, img_path)

    # 1. Feature Extraction
    gpu_flag = "1" if use_gpu else "0"
    cmd_extract = [
        "colmap",
        "feature_extractor",
        "--database_path",
        str(database_path),
        "--image_path",
        str(img_path),
        "--ImageReader.camera_model",
        camera_model,
        "--ImageReader.single_camera",
        "1",
        "--SiftExtraction.use_gpu",
        gpu_flag,
    ]
    logger.info("Executing: %s", " ".join(cmd_extract))
    res_extract = subprocess.run(cmd_extract, check=False, capture_output=True, text=True)
    if res_extract.returncode != 0:
        if use_gpu and ("CUDA" in res_extract.stderr or "gpu" in res_extract.stderr.lower()):
            logger.warning("GPU feature extraction failed. Falling back to CPU SIFT...")
            cmd_extract[-1] = "0"
            subprocess.run(cmd_extract, check=True)
        else:
            raise RuntimeError(f"COLMAP feature extraction failed:\n{res_extract.stderr}")

    # 2. Matching (exhaustive vs sequential based on frame count)
    use_exhaustive = (matcher == "exhaustive") or (
        matcher == "auto" and total_images <= matcher_auto_threshold
    )
    if use_exhaustive:
        logger.info("Using EXHAUSTIVE matcher (%d frames <= %d)", total_images, matcher_auto_threshold)
        cmd_match = [
            "colmap",
            "exhaustive_matcher",
            "--database_path",
            str(database_path),
            "--SiftMatching.use_gpu",
            gpu_flag,
        ]
    else:
        logger.info("Using SEQUENTIAL matcher (%d frames > %d)", total_images, matcher_auto_threshold)
        cmd_match = [
            "colmap",
            "sequential_matcher",
            "--database_path",
            str(database_path),
            "--SequentialMatching.overlap",
            str(overlap_window),
            "--SequentialMatching.loop_detection",
            "1" if loop_detection else "0",
            "--SiftMatching.use_gpu",
            gpu_flag,
        ]

    logger.info("Executing: %s", " ".join(cmd_match))
    res_match = subprocess.run(cmd_match, check=False, capture_output=True, text=True)
    if res_match.returncode != 0:
        if use_gpu:
            logger.warning("GPU matching failed. Falling back to CPU matching...")
            cmd_match[-1] = "0"
            subprocess.run(cmd_match, check=True)
        else:
            raise RuntimeError(f"COLMAP matcher failed:\n{res_match.stderr}")

    # 3. Sparse Mapper
    cmd_map = [
        "colmap",
        "mapper",
        "--database_path",
        str(database_path),
        "--image_path",
        str(img_path),
        "--output_path",
        str(sparse_dir),
    ]
    logger.info("Executing: %s", " ".join(cmd_map))
    res_map = subprocess.run(cmd_map, check=False, capture_output=True, text=True)
    if res_map.returncode != 0:
        raise RuntimeError(f"COLMAP mapper failed:\n{res_map.stderr}")

    # 4. Select the best sub-model if multiple components exist
    primary_model = select_best_sparse_model(sparse_dir)

    # 5. Analyze model using colmap model_analyzer (parsing both stdout and stderr)
    cmd_analyze = [
        "colmap",
        "model_analyzer",
        "--path",
        str(primary_model),
    ]
    logger.info("Executing: %s", " ".join(cmd_analyze))
    res_analyze = subprocess.run(cmd_analyze, check=False, capture_output=True, text=True)
    combined_output = res_analyze.stdout + "\n" + res_analyze.stderr

    if res_analyze.returncode != 0:
        raise RuntimeError(
            f"COLMAP model_analyzer failed on {primary_model}:\n{combined_output}"
        )

    parsed = parse_model_analyzer_output(combined_output)
    reg_images = parsed["registered_images"]
    tot_images = parsed["total_images"]
    reg_ratio = reg_images / max(1, tot_images)

    logger.info(
        "COLMAP Analysis: %d/%d registered (%.1f%%), %d 3D points, mean reproj error: %s px",
        reg_images,
        tot_images,
        reg_ratio * 100,
        parsed["points_count"],
        parsed["mean_reprojection_error_px"],
    )

    if reg_ratio < min_registered_ratio:
        raise RuntimeError(
            f"COLMAP registration failed quality gate: only {reg_images}/{tot_images} "
            f"({reg_ratio:.1%}) registered, below required {min_registered_ratio:.0%}"
        )

    elapsed = time.time() - start_time
    metrics = {
        "stage": "sfm",
        "elapsed_seconds": round(elapsed, 2),
        "total_images": tot_images,
        "registered_images": reg_images,
        "registration_ratio": round(reg_ratio, 4),
        "points_count": parsed["points_count"],
        "mean_reprojection_error_px": parsed["mean_reprojection_error_px"],
        "camera_model": camera_model,
        "sparse_model_dir": str(primary_model.resolve()),
    }

    metrics_file = out_path / "sfm_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics
