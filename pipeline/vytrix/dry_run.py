"""Dry-run smoke test runner for VYTRIX reconstruction pipeline.

Runs a fast end-to-end smoke test on a short 30-60 second smartphone video clip
(with 30 extracted frames and 200 training steps) to validate CUDA, COLMAP,
Ninja JIT compiler, and dependencies in ~3-5 minutes before executing the full
reconstruction.

Note: COLMAP requires genuine 3D parallax to triangulate feature points, so a
real video clip must be provided via --video.
"""

from __future__ import annotations

import argparse
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
)
from vytrix.optimize import compress_and_optimize_splat, parse_ply_header
from vytrix.package import package_scene
from vytrix.preprocess import extract_frames
from vytrix.sfm import run_colmap_sfm
from vytrix.train import train_gaussian_splat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vytrix.dry_run")


def run_dry_run_smoke_test(
    video_path: str | Path | None = None,
    work_dir: str | Path = "data/dry_run_work",
) -> dict[str, str]:
    """Execute fast smoke test of all 6 stages and return PASS/FAIL report."""
    results: dict[str, str] = {}
    w_dir = Path(work_dir)
    w_dir.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print("      VYTRIX PIPELINE DRY RUN & SYSTEM SMOKE TEST      ")
    print("=======================================================")

    if not video_path:
        err = (
            "Dry-run smoke test requires a real 30-60 second smartphone video clip (pass --video path/to/clip.mp4). "
            "COLMAP Structure-from-Motion requires genuine multiview 3D parallax to triangulate feature points "
            "and cannot reconstruct synthetic 2D frames."
        )
        print(f"[FAIL] Parameter Error: {err}")
        results["Input Video Verification"] = f"FAIL ({err})"
        return results

    vid_p = Path(video_path)
    if not vid_p.exists():
        err = f"Input video file not found at: {vid_p.resolve()}"
        print(f"[FAIL] Input Video Verification: {err}")
        results["Input Video Verification"] = f"FAIL ({err})"
        return results

    total_start = time.time()

    # Stage 1: Preprocess (~30 frames)
    t0 = time.time()
    s1_out = w_dir / "preprocess"
    try:
        s1_manifest = extract_frames(
            video_path=vid_p,
            output_dir=s1_out,
            target_frames=30,
            blur_threshold=10.0,
            downscale_factor=2,
        )
        dt = time.time() - t0
        frames_dir = s1_out / "frames"
        frame_files = list(frames_dir.glob("*.jpg")) + list(frames_dir.glob("*.png"))
        manifest1 = s1_out / "preprocess_manifest.json"

        # Explicit measured condition checks
        if not manifest1.exists() or manifest1.stat().st_size == 0:
            raise RuntimeError("preprocess_manifest.json was not generated or is 0 bytes.")
        if len(frame_files) < 15:
            raise RuntimeError(f"Only {len(frame_files)} frames extracted; minimum 15 required for SfM.")
        if s1_manifest["selected_frames_count"] != len(frame_files):
            raise RuntimeError("Frame count mismatch between manifest and directory.")

        results["Stage 1 (Preprocess)"] = f"PASS ({len(frame_files)} frames, size {manifest1.stat().st_size}B, {dt:.1f}s)"
        print(f"[PASS] Stage 1 (Preprocess): Extracted {len(frame_files)} frames ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 1 (Preprocess)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 1 (Preprocess): {e}")
        return results

    # Stage 2: COLMAP SfM
    t0 = time.time()
    s2_out = w_dir / "sfm"
    try:
        sfm_res = run_colmap_sfm(
            images_dir=frames_dir,
            output_dir=s2_out,
            camera_model="SIMPLE_RADIAL",
            matcher="exhaustive",
            matcher_auto_threshold=300,
            use_gpu=True,
            min_registered_ratio=0.30,  # Minimum 30% for short smoke clip
        )
        dt = time.time() - t0
        manifest2 = s2_out / "sfm_metrics.json"
        sparse_model = Path(sfm_res["sparse_model_dir"])
        reg = sfm_res["registered_images"]
        tot = sfm_res["total_images"]
        pts = sfm_res["points_count"]

        # Explicit measured condition checks
        if not manifest2.exists() or manifest2.stat().st_size == 0:
            raise RuntimeError("sfm_metrics.json was not generated or is 0 bytes.")
        if reg < 5:
            raise RuntimeError(f"COLMAP only registered {reg}/{tot} images (minimum 5 required).")
        if pts < 20:
            raise RuntimeError(f"Only {pts} 3D points triangulated (minimum 20 required).")
        has_cameras = (sparse_model / "cameras.bin").exists() or (sparse_model / "cameras.txt").exists()
        has_images = (sparse_model / "images.bin").exists() or (sparse_model / "images.txt").exists()
        if not (has_cameras and has_images):
            raise RuntimeError(f"Sparse model directory {sparse_model} missing cameras/images files.")

        results["Stage 2 (COLMAP SfM)"] = f"PASS ({reg}/{tot} registered, {pts} points, {dt:.1f}s)"
        print(f"[PASS] Stage 2 (COLMAP SfM): {reg}/{tot} images registered ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 2 (COLMAP SfM)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 2 (COLMAP SfM): {e}")
        return results

    # Stage 3: Splat Training (200 steps to trigger CUDA kernel JIT)
    t0 = time.time()
    s3_out = w_dir / "train"
    try:
        train_res = train_gaussian_splat(
            data_dir=sparse_model,
            output_dir=s3_out,
            iterations=200,
            sh_degree=1,
        )
        dt = time.time() - t0
        raw_ply = Path(train_res["ply_file"])
        manifest3 = s3_out / "train_metrics.json"

        # Explicit measured condition checks
        if not manifest3.exists() or manifest3.stat().st_size == 0:
            raise RuntimeError("train_metrics.json was not generated or is 0 bytes.")
        if not raw_ply.exists():
            raise RuntimeError(f"Trained PLY point cloud missing: {raw_ply}")
        if raw_ply.stat().st_size < 1000:
            raise RuntimeError(f"Trained PLY {raw_ply} is corrupt/empty ({raw_ply.stat().st_size} bytes).")

        v_cnt, _, _ = parse_ply_header(raw_ply.read_bytes()[:4096])
        if v_cnt < 20:
            raise RuntimeError(f"Only {v_cnt} Gaussians generated (minimum 20 required).")

        results["Stage 3 (3DGS Training)"] = f"PASS ({v_cnt} Gaussians, {raw_ply.stat().st_size}B in {dt:.1f}s)"
        print(f"[PASS] Stage 3 (3DGS Training): {v_cnt} Gaussians trained ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 3 (3DGS Training)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 3 (3DGS Training): {e}")
        return results

    # Stage 4: Normalization
    t0 = time.time()
    s4_out = w_dir / "normalize"
    s4_out.mkdir(parents=True, exist_ok=True)
    try:
        camera_centers, camera_ups = load_colmap_camera_poses(sparse_model)
        with open(raw_ply, "rb") as f:
            h_bytes = f.read(4096)
        v_cnt, props, offset = parse_ply_header(h_bytes)
        type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
        dt_ply = np.dtype([(n, type_map.get(t, "<f4")) for n, t in props])
        with open(raw_ply, "rb") as f:
            f.seek(offset)
            pts_data = np.fromfile(f, dtype=dt_ply, count=v_cnt)
        pts = np.stack([pts_data["x"], pts_data["y"], pts_data["z"]], axis=-1)

        scale_factor, _scale_method, _ = compute_scale_factor(None, None, 1.0)
        _trans_pts, transform_matrix, meta = normalize_scene(
            points=pts,
            camera_centers=camera_centers,
            camera_up_vectors=camera_ups,
            scale_factor=scale_factor,
        )
        norm_ply = s4_out / "normalized_splat.ply"
        normalize_splat_ply(raw_ply, norm_ply, transform_matrix, scale_factor=scale_factor)
        dt = time.time() - t0

        manifest4 = s4_out / "normalization_manifest.json"
        # Explicit measured condition checks
        if not manifest4.exists() or manifest4.stat().st_size == 0:
            raise RuntimeError("normalization_manifest.json missing.")
        if not norm_ply.exists() or norm_ply.stat().st_size < 1000:
            raise RuntimeError("normalized_splat.ply missing or corrupt.")
        if meta["bounds"]["min"][1] != 0.0:
            raise RuntimeError(f"Floor Y not leveled to 0.0 (got {meta['bounds']['min'][1]}).")

        results["Stage 4 (Normalization)"] = f"PASS (Floor leveled to Y=0, inlier ratio {meta['inlier_ratio']:.2f}, {dt:.1f}s)"
        print(f"[PASS] Stage 4 (Normalization): Floor leveled to Y=0 ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 4 (Normalization)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 4 (Normalization): {e}")
        return results

    # Stage 5: Splat Optimization & Packing
    t0 = time.time()
    s5_out = w_dir / "optimize"
    try:
        _ = compress_and_optimize_splat(
            input_ply_path=norm_ply,
            output_dir=s5_out,
            opacity_threshold=0.01,
            export_format="splat",
        )
        dt = time.time() - t0
        manifest5 = s5_out / "optimize_manifest.json"
        splat_file = s5_out / "scene.splat"

        # Explicit measured condition checks
        if not manifest5.exists() or manifest5.stat().st_size == 0:
            raise RuntimeError("optimize_manifest.json missing.")
        if not splat_file.exists():
            raise RuntimeError("scene.splat missing.")
        file_bytes = splat_file.stat().st_size
        if file_bytes == 0 or file_bytes % 32 != 0:
            raise RuntimeError(f"scene.splat size ({file_bytes} B) is not a non-zero multiple of 32 bytes.")
        n_gauss = file_bytes // 32
        if n_gauss < 10:
            raise RuntimeError(f"Only {n_gauss} Gaussians packed (minimum 10 required).")

        results["Stage 5 (Optimize)"] = f"PASS ({n_gauss} Gaussians, {file_bytes}B, {dt:.1f}s)"
        print(f"[PASS] Stage 5 (Optimize): {n_gauss} Gaussians packed to 32-byte .splat ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 5 (Optimize)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 5 (Optimize): {e}")
        return results

    # Stage 6: Packaging
    t0 = time.time()
    try:
        config = load_config("config.yaml")
        scene_manifest = package_scene(
            config=config,
            stage_dir=w_dir,
            viewer_scenes_dir="viewer/public/scenes",
        )
        dt = time.time() - t0
        manifest6 = Path("viewer/public/scenes/default/scene.json")
        target_splat = Path("viewer/public/scenes/default/scene.splat")

        # Explicit measured condition checks
        if not manifest6.exists() or manifest6.stat().st_size == 0:
            raise RuntimeError("viewer scene.json missing or empty.")
        if not target_splat.exists() or target_splat.stat().st_size == 0:
            raise RuntimeError("viewer scene.splat missing or empty.")
        for req_field in ["scene_id", "splat", "transform_applied", "bounds", "spawn", "metrics"]:
            if req_field not in scene_manifest:
                raise RuntimeError(f"scene.json missing required field '{req_field}'.")

        results["Stage 6 (Packaging)"] = f"PASS (Manifest valid, splat {target_splat.stat().st_size}B in {dt:.1f}s)"
        print(f"[PASS] Stage 6 (Packaging): Manifest generated ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 6 (Packaging)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 6 (Packaging): {e}")
        return results

    total_dt = time.time() - total_start
    print("\n-------------------------------------------------------")
    print(f"DRY RUN SUMMARY: ALL 6 STAGES PASSED in {total_dt:.1f}s (~{total_dt/60:.1f} min)")
    print("Environment is verified and ready for full video capture reconstruction.")
    print("-------------------------------------------------------\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="VYTRIX Dry-Run Smoke Test Runner")
    parser.add_argument("--video", type=str, required=True, help="Path to real 30-60s smartphone video clip")
    parser.add_argument("--work-dir", type=str, default="data/dry_run_work", help="Dry run output directory")
    args = parser.parse_args()

    results = run_dry_run_smoke_test(video_path=args.video, work_dir=args.work_dir)
    failed = [k for k, v in results.items() if "FAIL" in v]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
