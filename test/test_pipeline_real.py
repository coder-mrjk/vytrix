"""Unit tests verifying real mathematical operations and evidence-based pipeline rules."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import pytest
from vytrix.normalize import (
    compute_scale_factor,
    fit_floor_plane_ransac,
    normalize_splat_ply,
)
from vytrix.optimize import convert_ply_to_splat, parse_ply_header
from vytrix.package import package_scene
from vytrix.train import parse_trainer_eval_metrics


def test_floor_detection_with_camera_guidance_and_decoys():
    """Verify floor detection selects true floor despite wall and ceiling decoys with more inliers."""
    # 1. Floor points at Y = -1.0 (200 inliers)
    rng = np.random.default_rng(42)
    floor_pts = np.zeros((200, 3))
    floor_pts[:, 0] = rng.uniform(-3, 3, 200)
    floor_pts[:, 2] = rng.uniform(-3, 3, 200)
    floor_pts[:, 1] = -1.0 + rng.normal(0, 0.005, 200)

    # 2. Ceiling decoy at Y = +2.5 with MORE inliers (300 inliers)
    ceiling_pts = np.zeros((300, 3))
    ceiling_pts[:, 0] = rng.uniform(-3, 3, 300)
    ceiling_pts[:, 2] = rng.uniform(-3, 3, 300)
    ceiling_pts[:, 1] = 2.5 + rng.normal(0, 0.005, 300)

    # 3. Wall decoy at X = +3.0 with EVEN MORE inliers (400 inliers)
    wall_pts = np.zeros((400, 3))
    wall_pts[:, 1] = rng.uniform(-1, 2.5, 400)
    wall_pts[:, 2] = rng.uniform(-3, 3, 400)
    wall_pts[:, 0] = 3.0 + rng.normal(0, 0.005, 400)

    all_pts = np.vstack([floor_pts, ceiling_pts, wall_pts])

    # Cameras situated between floor and ceiling at Y = 0.5, looking around with +Y up
    camera_centers = np.array([
        [0.0, 0.5, 0.0],
        [1.0, 0.5, 0.5],
        [-1.0, 0.5, -0.5],
    ])
    camera_ups = np.array([
        [0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
    ])

    plane, inliers = fit_floor_plane_ransac(
        points=all_pts,
        camera_centers=camera_centers,
        camera_up_vectors=camera_ups,
        distance_threshold=0.03,
        max_iterations=1000,
        min_inliers=100,
    )

    # Normal must point upward (+Y)
    normal = plane[:3]
    d = plane[3]
    np.testing.assert_allclose(normal, np.array([0.0, 1.0, 0.0]), atol=0.05)
    # Floor level d should be approx +1.0 (since Y = -1.0 -> 1*(-1) + 1 = 0)
    assert np.isclose(d, 1.0, atol=0.05)
    # The vast majority of detected inliers must be from the floor points (indices 0..199)
    floor_inliers = [idx for idx in inliers if idx < 200]
    assert len(floor_inliers) >= 190


def test_floor_detection_fails_loudly_when_no_valid_floor():
    """Verify fit_floor_plane_ransac raises RuntimeError when no plane matches constraints."""
    # Only vertical wall points
    rng = np.random.default_rng(99)
    wall_pts = np.zeros((100, 3))
    wall_pts[:, 1] = rng.uniform(-2, 2, 100)
    wall_pts[:, 2] = rng.uniform(-2, 2, 100)
    wall_pts[:, 0] = 1.0 + rng.normal(0, 0.01, 100)

    camera_centers = np.array([[0.0, 0.0, 0.0]])
    camera_ups = np.array([[0.0, 1.0, 0.0]])

    with pytest.raises(RuntimeError, match="Floor plane detection failed"):
        fit_floor_plane_ransac(
            points=wall_pts,
            camera_centers=camera_centers,
            camera_up_vectors=camera_ups,
            min_inliers=50,
        )


def test_scale_from_clicked_points_and_uncalibrated_fallback():
    """Verify metric scale computation from two points or graceful uncalibrated fallback."""
    # 1. Uncalibrated fallback
    s, method, err = compute_scale_factor(None, None, 1.00)
    assert s == 1.0
    assert method == "uncalibrated"
    assert err is None

    # 2. Calibrated two-point distance
    # SfM distance = 2.0 metres, real measured distance = 1.00 metre -> scale factor = 0.50
    p1 = [0.0, 0.0, 0.0]
    p2 = [2.0, 0.0, 0.0]
    s_cal, method_cal, err_cal = compute_scale_factor(p1, p2, 1.00)
    assert np.isclose(s_cal, 0.50)
    assert method_cal == "two_point_tape"
    assert err_cal is None

    # 3. Degenerate identical points fallback
    s_deg, method_deg, _ = compute_scale_factor([1.0, 1.0, 1.0], [1.0, 1.0, 1.0], 1.00)
    assert s_deg == 1.0
    assert method_deg == "uncalibrated"


def _create_synthetic_ply(file_path: Path, gaussians: list[dict[str, float]]) -> None:
    """Helper to write binary little-endian 3DGS PLY file for tests."""
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {len(gaussians)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property float opacity\n"
        "property float scale_0\n"
        "property float scale_1\n"
        "property float scale_2\n"
        "property float rot_0\n"
        "property float rot_1\n"
        "property float rot_2\n"
        "property float rot_3\n"
        "property float f_dc_0\n"
        "property float f_dc_1\n"
        "property float f_dc_2\n"
        "end_header\n"
    )

    with open(file_path, "wb") as f:
        f.write(header.encode("ascii"))
        for g in gaussians:
            data = struct.pack(
                "<ffffffffffffff",
                g["x"], g["y"], g["z"],
                g["opacity"],
                g["scale_0"], g["scale_1"], g["scale_2"],
                g["rot_0"], g["rot_1"], g["rot_2"], g["rot_3"],
                g["f_dc_0"], g["f_dc_1"], g["f_dc_2"],
            )
            f.write(data)


def test_ply_to_splat_conversion_and_pruning(tmp_path: Path):
    """Verify that PLY to .splat prunes low opacity and packs exact 32-byte records."""
    ply_path = tmp_path / "test_model.ply"
    splat_path = tmp_path / "output.splat"

    # 4 Gaussians: 2 high opacity (keep), 2 low opacity (prune)
    gaussians = [
        # Keep (opacity logit +4.0 -> sigmoid ~0.982)
        {
            "x": 1.0, "y": 2.0, "z": 3.0,
            "opacity": 4.0,
            "scale_0": -1.0, "scale_1": -1.0, "scale_2": -1.0,
            "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": 1.0, "f_dc_1": 0.5, "f_dc_2": -0.5,
        },
        # Prune (opacity logit -5.0 -> sigmoid ~0.0067 < 0.05)
        {
            "x": 0.0, "y": 0.0, "z": 0.0,
            "opacity": -5.0,
            "scale_0": 0.0, "scale_1": 0.0, "scale_2": 0.0,
            "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": 0.0, "f_dc_1": 0.0, "f_dc_2": 0.0,
        },
        # Keep (opacity logit +2.0 -> sigmoid ~0.880)
        {
            "x": -1.5, "y": 0.5, "z": 2.5,
            "opacity": 2.0,
            "scale_0": -2.0, "scale_1": -2.0, "scale_2": -2.0,
            "rot_0": 0.0, "rot_1": 1.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": -0.5, "f_dc_1": 1.0, "f_dc_2": 0.0,
        },
        # Prune (opacity logit -10.0)
        {
            "x": 5.0, "y": 5.0, "z": 5.0,
            "opacity": -10.0,
            "scale_0": 0.0, "scale_1": 0.0, "scale_2": 0.0,
            "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": 0.0, "f_dc_1": 0.0, "f_dc_2": 0.0,
        },
    ]

    _create_synthetic_ply(ply_path, gaussians)

    stats = convert_ply_to_splat(ply_path, splat_path, opacity_threshold=0.05)

    assert stats["initial_gaussians"] == 4
    assert stats["pruned_gaussians"] == 2
    assert stats["final_bytes"] == 2 * 32  # Exactly 64 bytes for 2 Gaussians

    # Read and inspect binary records
    with open(splat_path, "rb") as f:
        data = f.read()

    assert len(data) == 64

    # First Gaussian check
    pos = struct.unpack("<fff", data[0:12])
    scales = struct.unpack("<fff", data[12:24])
    colors = struct.unpack("<BBBB", data[24:28])

    np.testing.assert_allclose(pos, (1.0, 2.0, 3.0), atol=1e-5)
    np.testing.assert_allclose(scales, (np.exp(-1.0), np.exp(-1.0), np.exp(-1.0)), atol=1e-5)
    # Alpha = round(sigmoid(4.0) * 255) = round(0.9820 * 255) = 250
    assert colors[3] == 250
    # Red = round((0.5 + 0.28209479 * 1.0) * 255) = round(0.78209 * 255) = 199
    assert colors[0] == 199


def test_manifest_null_handling(tmp_path: Path):
    """Verify that unmeasured metrics are strictly serialized as null, not invented."""
    # 1. Test eval log parser with un-evaluated output
    eval_metrics = parse_trainer_eval_metrics("Optimization step 15000 complete. Checkpoint saved.")
    assert eval_metrics["psnr"] is None
    assert eval_metrics["ssim"] is None

    # 2. Test package_scene with minimal config
    stage_dir = tmp_path / "work"
    stage_dir.mkdir(parents=True)
    viewer_dir = tmp_path / "viewer"

    # Stage 5 output: valid dummy 32-byte splat
    opt_dir = stage_dir / "optimize"
    opt_dir.mkdir(parents=True)
    with open(opt_dir / "scene.splat", "wb") as f:
        f.write(b"\x00" * 64)  # 2 Gaussians

    with open(opt_dir / "optimize_manifest.json", "w", encoding="utf-8") as f:
        json.dump({"pruned_gaussians": 2, "output_file_size_bytes": 64}, f)

    config = {
     "project": {"name": "VYTRIX", "scene_id": "test-scene"},
     "viewer": {"title": "Test Scene", "camera": {"eye_height_m": 1.6}},
    }

    manifest = package_scene(
        config=config,
        stage_dir=stage_dir,
        viewer_scenes_dir=viewer_dir,
    )

    # Required evidence checks: unmeasured metrics must be None
    assert manifest["metrics"]["registered_images"] is None
    assert manifest["metrics"]["total_images"] is None
    assert manifest["metrics"]["reproj_error_px"] is None
    assert manifest["metrics"]["psnr"] is None
    assert manifest["metrics"]["ssim"] is None
    assert manifest["splat"]["num_gaussians"] == 2


def test_normalize_splat_ply_transform(tmp_path: Path):
    """Verify that normalize_splat_ply correctly transforms positions, scales, and quaternions."""
    in_ply = tmp_path / "raw.ply"
    out_ply = tmp_path / "norm.ply"

    gaussians = [
        {
            "x": 1.0, "y": 2.0, "z": 0.0,
            "opacity": 2.0,
            "scale_0": 0.0, "scale_1": 0.0, "scale_2": 0.0,
            "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": 0.5, "f_dc_1": 0.5, "f_dc_2": 0.5,
        }
    ]
    _create_synthetic_ply(in_ply, gaussians)

    # 4x4 matrix: 2x scale, Y shift of -1.0
    transform_matrix = np.eye(4)
    transform_matrix[0, 0] = 2.0
    transform_matrix[1, 1] = 2.0
    transform_matrix[2, 2] = 2.0
    transform_matrix[1, 3] = -1.0

    normalize_splat_ply(in_ply, out_ply, transform_matrix, scale_factor=2.0)

    assert out_ply.exists()
    v_cnt, props, offset = parse_ply_header(out_ply.read_bytes())
    assert v_cnt == 1

    type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
    dt = np.dtype([(n, type_map.get(t, "<f4")) for n, t in props])
    with open(out_ply, "rb") as f:
        f.seek(offset)
        transformed = np.fromfile(f, dtype=dt, count=1)[0]

    # Transformed pos: x = 1*2 = 2.0, y = 2*2 - 1 = 3.0, z = 0
    assert np.isclose(transformed["x"], 2.0)
    assert np.isclose(transformed["y"], 3.0)
    assert np.isclose(transformed["z"], 0.0)

    # Scale in log-space: 0 + ln(2.0)
    assert np.isclose(transformed["scale_0"], np.log(2.0), atol=1e-5)

