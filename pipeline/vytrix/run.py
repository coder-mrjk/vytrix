"""End-to-end CLI orchestrator for VYTRIX 3D Reconstruction Pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

from vytrix.config import load_config
from vytrix.normalize import (
    compute_scale_factor,
    load_colmap_camera_poses,
    normalize_scene,
    normalize_splat_ply,
    read_colmap_sparse_points,
)
from vytrix.optimize import compress_and_optimize_splat, parse_ply_header
from vytrix.package import package_scene
from vytrix.preprocess import extract_frames
from vytrix.sfm import run_colmap_sfm
from vytrix.train import train_gaussian_splat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vytrix.run")


def run_pipeline(
    video_path: str | Path | None,
    config_path: str | Path = "config.yaml",
    work_dir: str | Path = "data/work",
    force: bool = False,
    from_stage: int = 1,
    scale_p1: list[float] | None = None,
    scale_p2: list[float] | None = None,
    scale_distance: float | None = 1.0,
    viewer_scenes_dir: str | Path = "viewer/public/scenes",
) -> None:
    """Run all stages of the VYTRIX reconstruction pipeline idempotently.

    Args:
        video_path: Path to captured smartphone video file.
        config_path: Path to configuration YAML.
        work_dir: Working directory for intermediate outputs.
        force: If True, re-runs stages even if output manifests exist.
    """
    total_start = time.time()
    config = load_config(config_path)
    w_dir = Path(work_dir)
    w_dir.mkdir(parents=True, exist_ok=True)

    logger.info("==================================================")
    logger.info("   VYTRIX Reconstruction Pipeline (VYTRO SQUAD)   ")
    logger.info("==================================================")

    # Stage 1: Preprocessing (Frame Extraction & Blur Filter)
    stage1_out = w_dir / "preprocess"
    manifest1 = stage1_out / "preprocess_manifest.json"
    if from_stage > 1 or (manifest1.exists() and not force):
        logger.info("[SKIP] Stage 1 (Preprocess) output already exists (or from_stage > 1).")
    else:
        if not video_path:
            logger.warning("No video path provided; skipping Stage 1 extraction.")
        else:
            logger.info("[RUN] Stage 1: Preprocessing video frames...")
            cfg_pre = config.get("preprocess", {})
            extract_frames(
                video_path=video_path,
                output_dir=stage1_out,
                target_frames=cfg_pre.get("target_frames", 350),
                blur_threshold=cfg_pre.get("blur_threshold_variance", 100.0),
                downscale_factor=cfg_pre.get("downscale_factor", 1),
            )

    # Stage 2: COLMAP SfM
    stage2_out = w_dir / "sfm"
    manifest2 = stage2_out / "sfm_metrics.json"
    if from_stage > 2 or (manifest2.exists() and not force):
        logger.info("[SKIP] Stage 2 (SfM) output already exists (or from_stage > 2).")
    else:
        logger.info("[RUN] Stage 2: COLMAP Structure-from-Motion...")
        cfg_sfm = config.get("sfm", {})
        frames_dir = stage1_out / "frames"
        if frames_dir.exists():
            run_colmap_sfm(
                images_dir=frames_dir,
                output_dir=stage2_out,
                camera_model=cfg_sfm.get("camera_model", "SIMPLE_RADIAL"),
                matcher=cfg_sfm.get("matcher", "auto"),
                matcher_auto_threshold=cfg_sfm.get("matcher_auto_threshold", 300),
                overlap_window=cfg_sfm.get("overlap_window", 20),
                loop_detection=cfg_sfm.get("loop_detection", True),
                min_registered_ratio=cfg_sfm.get("min_registered_ratio", 0.70),
                use_gpu=cfg_sfm.get("use_gpu", True),
            )

    # Stage 3: Splat Training
    stage3_out = w_dir / "train"
    manifest3 = stage3_out / "train_metrics.json"
    if from_stage > 3 or (manifest3.exists() and not force):
        logger.info("[SKIP] Stage 3 (Train) output already exists (or from_stage > 3); reusing trained model.")
    else:
        logger.info("[RUN] Stage 3: 3D Gaussian Splatting Training...")
        cfg_train = config.get("training", {})
        train_gaussian_splat(
            data_dir=stage2_out / "sparse",
            output_dir=stage3_out,
            iterations=cfg_train.get("iterations", 15000),
            sh_degree=cfg_train.get("sh_degree", 3),
            drive_checkpoint_dir=cfg_train.get("colab_drive_checkpoint_dir"),
        )

    # Stage 4: Scene Normalization
    stage4_out = w_dir / "normalize"
    manifest4 = stage4_out / "normalization_manifest.json"
    if from_stage > 4 or (manifest4.exists() and not force and not scale_p1):
        logger.info("[SKIP] Stage 4 (Normalize) output already exists.")
    else:
        logger.info("[RUN] Stage 4: Normalizing Scene Coordinates...")
        stage4_out.mkdir(parents=True, exist_ok=True)

        scale_factor, scale_method, _ = compute_scale_factor(scale_p1, scale_p2, scale_distance)

        # Locate COLMAP sparse directory for camera poses
        sparse_dir = stage2_out / "sparse" / "0"
        if not sparse_dir.exists():
            sparse_dir = stage2_out / "sparse"

        camera_centers = None
        camera_ups = None
        if sparse_dir.exists():
            try:
                camera_centers, camera_ups = load_colmap_camera_poses(sparse_dir)
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("Could not load camera poses from %s: %s", sparse_dir, e)

        raw_ply = stage3_out / "splat_raw.ply"
        if raw_ply.exists():
            logger.info("Normalizing trained splat point cloud: %s", raw_ply)
            with open(raw_ply, "rb") as f:
                header_data = f.read(4096)
            v_cnt, props, offset = parse_ply_header(header_data)
            type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
            dt = np.dtype([(n, type_map.get(t, "<f4")) for n, t in props])
            with open(raw_ply, "rb") as f:
                f.seek(offset)
                ply_points = np.fromfile(f, dtype=dt, count=v_cnt)
            pts = np.stack([ply_points["x"], ply_points["y"], ply_points["z"]], axis=-1)

            _transformed_pts, transform_matrix, meta = normalize_scene(
                points=pts,
                camera_centers=camera_centers,
                camera_up_vectors=camera_ups,
                scale_factor=scale_factor,
            )
            meta["scale_method"] = scale_method
            norm_ply = stage4_out / "normalized_splat.ply"
            normalize_splat_ply(raw_ply, norm_ply, transform_matrix, scale_factor=scale_factor)
        elif sparse_dir.exists():
            logger.info("No raw PLY found; fitting floor plane from COLMAP sparse cloud: %s", sparse_dir)
            sparse_pts = read_colmap_sparse_points(sparse_dir)
            _transformed_pts, transform_matrix, meta = normalize_scene(
                points=sparse_pts,
                camera_centers=camera_centers,
                camera_up_vectors=camera_ups,
                scale_factor=scale_factor,
            )
            meta["scale_method"] = scale_method
        else:
            raise FileNotFoundError(
                f"Cannot run Stage 4 normalization: neither trained splat ({raw_ply}) nor "
                f"COLMAP sparse model ({sparse_dir}) was found."
            )

        with open(manifest4, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    # Stage 5: Splat Optimization & Compression
    stage5_out = w_dir / "optimize"
    manifest5 = stage5_out / "optimize_manifest.json"
    if from_stage > 5 or (manifest5.exists() and not force and not scale_p1):
        logger.info("[SKIP] Stage 5 (Optimize) output already exists.")
    else:
        logger.info("[RUN] Stage 5: Splat Opacity Pruning & Web Compression...")
        norm_ply = stage4_out / "normalized_splat.ply"
        input_ply = norm_ply if norm_ply.exists() else (stage3_out / "splat_raw.ply")
        if not input_ply.exists():
            raise FileNotFoundError(
                f"Stage 5 requires normalized PLY at {norm_ply} or raw PLY at {stage3_out / 'splat_raw.ply'}"
            )
        compress_and_optimize_splat(
            input_ply_path=input_ply,
            output_dir=stage5_out,
            opacity_threshold=config.get("compression", {}).get("prune_opacity_threshold", 0.05),
            export_format=config.get("compression", {}).get("export_format", "splat"),
        )

    # Stage 6: Packaging
    logger.info("[RUN] Stage 6: Packaging scene into viewer public layout...")
    scene_manifest = package_scene(
        config=config,
        stage_dir=w_dir,
        viewer_scenes_dir=viewer_scenes_dir,
    )

    total_elapsed = time.time() - total_start
    logger.info("==================================================")
    logger.info("Pipeline completed successfully in %.2f seconds!", total_elapsed)
    logger.info("Scene ID: %s | Title: %s", scene_manifest["scene_id"], scene_manifest["title"])
    logger.info("==================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="VYTRIX Spatial Engine Pipeline Runner")
    parser.add_argument("--video", type=str, default=None, help="Path to input smartphone MP4")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--work-dir", type=str, default="data/work", help="Intermediate work directory")
    parser.add_argument("--force", action="store_true", help="Force rerun of all stages")
    parser.add_argument("--from-stage", type=int, default=1, choices=[1, 2, 3, 4, 5, 6], help="Resume pipeline starting from stage (e.g. 4 for scale recalibration without retraining)")
    parser.add_argument("--scale-points", type=str, default=None, help="Comma-separated 'x1,y1,z1,x2,y2,z2' for metric scale")
    parser.add_argument("--scale-distance", type=float, default=1.0, help="Real-world distance in metres between scale points")

    args = parser.parse_args()

    scale_p1 = None
    scale_p2 = None
    if args.scale_points:
        try:
            coords = [float(x.strip()) for x in args.scale_points.split(",")]
            if len(coords) == 6:
                scale_p1 = coords[:3]
                scale_p2 = coords[3:]
            else:
                logger.error("Expected 6 values for --scale-points (x1,y1,z1,x2,y2,z2), got %d", len(coords))
        except ValueError as e:
            logger.error("Invalid --scale-points values: %s", e)

    try:
        run_pipeline(
            video_path=args.video,
            config_path=args.config,
            work_dir=args.work_dir,
            force=args.force,
            from_stage=args.from_stage,
            scale_p1=scale_p1,
            scale_p2=scale_p2,
            scale_distance=args.scale_distance,
        )
    except Exception:
        logger.exception("Pipeline execution failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
