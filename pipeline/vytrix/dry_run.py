"""Dry-run smoke test runner for VYTRIX reconstruction pipeline.

Runs a fast end-to-end smoke test on a 30-frame clip (or 200 training steps)
to validate CUDA, COLMAP, Ninja JIT compiler, and dependencies in ~3-5 minutes
before executing the full capture reconstruction.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2
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


def create_synthetic_smoke_video(output_mp4: Path, num_frames: int = 30) -> Path:
    """Generate a minimal synthetic 30-frame MP4 video if no clip is available."""
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_mp4), fourcc, 15.0, (640, 480))

    for i in range(num_frames):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw moving high-contrast textured patterns
        cv2.rectangle(img, (50 + i * 5, 50), (200 + i * 5, 200), (0, 240, 255), -1)
        cv2.circle(img, (320, 240 + int(np.sin(i * 0.2) * 30)), 60, (255, 100, 50), -1)
        cv2.putText(img, f"VYTRIX SMOKE FRAME {i:03d}", (40, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        writer.write(img)

    writer.release()
    return output_mp4


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
    total_start = time.time()

    # Stage 1: Preprocess (~30 frames)
    t0 = time.time()
    s1_out = w_dir / "preprocess"
    try:
        vid_p = Path(video_path) if video_path else None
        if not vid_p or not vid_p.exists():
            synth_mp4 = w_dir / "smoke_clip.mp4"
            print("Notice: No input video specified; synthesizing 30-frame test clip...")
            vid_p = create_synthetic_smoke_video(synth_mp4, num_frames=30)

        s1_manifest = extract_frames(
            video_path=vid_p,
            output_dir=s1_out,
            target_frames=30,
            blur_threshold=10.0,
            downscale_factor=2,
        )
        dt = time.time() - t0
        frames_cnt = s1_manifest["selected_frames_count"]
        results["Stage 1 (Preprocess)"] = f"PASS ({frames_cnt} frames extracted in {dt:.1f}s)"
        print(f"[PASS] Stage 1 (Preprocess): Extracted {frames_cnt} frames ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 1 (Preprocess)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 1 (Preprocess): {e}")
        return results

    # Stage 2: COLMAP SfM
    t0 = time.time()
    s2_out = w_dir / "sfm"
    try:
        frames_dir = s1_out / "frames"
        sfm_res = run_colmap_sfm(
            images_dir=frames_dir,
            output_dir=s2_out,
            camera_model="SIMPLE_RADIAL",
            matcher="exhaustive",
            matcher_auto_threshold=300,
            use_gpu=True,
            min_registered_ratio=0.30,  # Lower threshold for smoke test clip
        )
        dt = time.time() - t0
        reg = sfm_res["registered_images"]
        tot = sfm_res["total_images"]
        results["Stage 2 (COLMAP SfM)"] = f"PASS ({reg}/{tot} registered in {dt:.1f}s)"
        print(f"[PASS] Stage 2 (COLMAP SfM): {reg}/{tot} images registered ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 2 (COLMAP SfM)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 2 (COLMAP SfM): {e}")
        return results

    # Stage 3: Splat Training (200 steps to trigger CUDA kernel JIT)
    t0 = time.time()
    s3_out = w_dir / "train"
    try:
        sparse_dir = s2_out / "sparse" / "0"
        if not sparse_dir.exists():
            sparse_dir = s2_out / "sparse"
        train_res = train_gaussian_splat(
            data_dir=sparse_dir,
            output_dir=s3_out,
            iterations=200,
            sh_degree=1,
        )
        dt = time.time() - t0
        results["Stage 3 (3DGS Training)"] = f"PASS (200 steps & CUDA compilation in {dt:.1f}s)"
        print(f"[PASS] Stage 3 (3DGS Training): 200 steps complete ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 3 (3DGS Training)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 3 (3DGS Training): {e}")
        return results

    # Stage 4: Normalization
    t0 = time.time()
    s4_out = w_dir / "normalize"
    s4_out.mkdir(parents=True, exist_ok=True)
    try:
        camera_centers, camera_ups = load_colmap_camera_poses(sparse_dir)
        raw_ply = Path(train_res["ply_file"])

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
        results["Stage 4 (Normalization)"] = f"PASS (Floor fitted at Y={meta['floor_level_y']:.2f} in {dt:.1f}s)"
        print(f"[PASS] Stage 4 (Normalization): Floor leveled to Y=0 ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 4 (Normalization)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 4 (Normalization): {e}")
        return results

    # Stage 5: Splat Optimization & Packing
    t0 = time.time()
    s5_out = w_dir / "optimize"
    try:
        opt_res = compress_and_optimize_splat(
            input_ply_path=norm_ply,
            output_dir=s5_out,
            opacity_threshold=0.01,
            export_format="splat",
        )
        dt = time.time() - t0
        n_gauss = opt_res["pruned_gaussians"]
        results["Stage 5 (Optimize)"] = f"PASS ({n_gauss} Gaussians packed in {dt:.1f}s)"
        print(f"[PASS] Stage 5 (Optimize): {n_gauss} Gaussians packed to 32-byte .splat ({dt:.1f}s)")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
        results["Stage 5 (Optimize)"] = f"FAIL ({e})"
        print(f"[FAIL] Stage 5 (Optimize): {e}")
        return results

    # Stage 6: Packaging
    t0 = time.time()
    try:
        config = load_config("config.yaml")
        _ = package_scene(
            config=config,
            stage_dir=w_dir,
            viewer_scenes_dir="viewer/public/scenes",
        )
        dt = time.time() - t0
        results["Stage 6 (Packaging)"] = f"PASS (scene.json generated in {dt:.1f}s)"
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
    parser.add_argument("--video", type=str, default=None, help="Optional 30-60s clip for smoke test")
    parser.add_argument("--work-dir", type=str, default="data/dry_run_work", help="Dry run output directory")
    args = parser.parse_args()

    results = run_dry_run_smoke_test(video_path=args.video, work_dir=args.work_dir)
    failed = [k for k, v in results.items() if "FAIL" in v]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
