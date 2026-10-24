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
from vytrix.sfm import parse_model_analyzer_output, select_best_sparse_model
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


def test_select_best_sparse_model_multiple_components(tmp_path: Path):
    """Verify select_best_sparse_model picks sub-model with maximum registered images."""
    sparse_root = tmp_path / "sparse"
    sparse_root.mkdir()

    # Sub-model 0: 30 images
    m0 = sparse_root / "0"
    m0.mkdir()
    with open(m0 / "images.txt", "w") as f:
        f.write("# Image list with two lines per image\n")
        f.writelines(f"{i} 1 0 0 0 0 0 0 1 frame_{i}.jpg\n\n" for i in range(30))

    # Sub-model 1: 180 images (largest component)
    m1 = sparse_root / "1"
    m1.mkdir()
    with open(m1 / "images.txt", "w") as f:
        f.write("# Image list with two lines per image\n")
        f.writelines(f"{i} 1 0 0 0 0 0 0 1 frame_{i}.jpg\n\n" for i in range(180))

    # Sub-model 2: 15 images
    m2 = sparse_root / "2"
    m2.mkdir()
    with open(m2 / "images.txt", "w") as f:
        f.write("# Image list with two lines per image\n")
        f.writelines(f"{i} 1 0 0 0 0 0 0 1 frame_{i}.jpg\n\n" for i in range(15))

    best = select_best_sparse_model(sparse_root)
    assert best == m1
    assert best.name == "1"


def test_parse_model_analyzer_combined_stdout_stderr():
    """Verify parse_model_analyzer_output parses images and reprojection error from combined output."""
    sample_colmap_output = (
        "Reading reconstruction...\n"
        "----------------------------------------------------------------\n"
        "Model statistics:\n"
        "----------------------------------------------------------------\n"
        "Cameras: 1\n"
        "Images: 350\n"
        "Registered images: 342\n"
        "Points: 48921\n"
        "Mean track length: 4.821\n"
        "Mean observations per image: 681.3\n"
        "Mean reprojection error: 0.693 px\n"
        "----------------------------------------------------------------\n"
    )

    parsed = parse_model_analyzer_output(sample_colmap_output)
    assert parsed["total_images"] == 350
    assert parsed["registered_images"] == 342
    assert parsed["points_count"] == 48921
    assert parsed["mean_reprojection_error_px"] == 0.693


def test_pass2_rescaling_floor_and_distance(tmp_path: Path):
    """Verify Pass 2 (--from-stage 4 with --scale-points):

    1. Reuses Stage 3 trained model without retraining.
    2. Levels floor to Y=0 with bounds.min[1] within 1e-6.
    3. Re-scales model such that distance between picked points equals real distance within 1%.
    4. Computes floor offset strictly after metric scaling.
    """
    from vytrix.run import run_pipeline

    work_dir = tmp_path / "work"
    stage2_sparse = work_dir / "sfm" / "sparse" / "0"
    stage2_sparse.mkdir(parents=True)
    stage3_train = work_dir / "train"
    stage3_train.mkdir(parents=True)

    # 1. Setup Stage 2 camera pose: camera at (0, 1.5, 0) looking forward, up vector = [0, 1, 0]
    with open(stage2_sparse / "images.txt", "w") as f:
        f.write("# Image list\n")
        f.write("1 0.0 1.0 0.0 0.0 0.0 1.5 0.0 1 frame_001.jpg\n\n")

    # 2. Setup Stage 3 trained output (splat_raw.ply)
    rng = np.random.default_rng(123)
    gaussians = []
    # Two calibration points on the floor with SfM distance = 0.50 m
    p1_sfm = [-0.25, -0.5, 0.0]
    p2_sfm = [0.25, -0.5, 0.0]

    gaussians.append({
        "x": p1_sfm[0], "y": p1_sfm[1], "z": p1_sfm[2],
        "opacity": 5.0,
        "scale_0": -2.0, "scale_1": -2.0, "scale_2": -2.0,
        "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
        "f_dc_0": 0.5, "f_dc_1": 0.5, "f_dc_2": 0.5,
    })
    gaussians.append({
        "x": p2_sfm[0], "y": p2_sfm[1], "z": p2_sfm[2],
        "opacity": 5.0,
        "scale_0": -2.0, "scale_1": -2.0, "scale_2": -2.0,
        "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
        "f_dc_0": 0.5, "f_dc_1": 0.5, "f_dc_2": 0.5,
    })

    # Add 100 floor points at Y = -0.5
    for _ in range(100):
        gaussians.append({
            "x": float(rng.uniform(-2, 2)),
            "y": -0.5 + float(rng.normal(0, 0.002)),
            "z": float(rng.uniform(-2, 2)),
            "opacity": 4.0,
            "scale_0": -2.0, "scale_1": -2.0, "scale_2": -2.0,
            "rot_0": 1.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 0.0,
            "f_dc_0": 0.5, "f_dc_1": 0.5, "f_dc_2": 0.5,
        })

    raw_ply = stage3_train / "splat_raw.ply"
    _create_synthetic_ply(raw_ply, gaussians)

    train_manifest = stage3_train / "train_metrics.json"
    with open(train_manifest, "w") as f:
        json.dump({"iterations": 15000, "ply_file": str(raw_ply.resolve())}, f)
    stage3_mtime_before = train_manifest.stat().st_mtime

    # 3. Execute Pass 2: from_stage=4, scale_distance = 1.00 m
    # SfM distance is 0.50 m, so scale factor must be 1.00 / 0.50 = 2.00
    run_pipeline(
        video_path=None,
        config_path="config.yaml",
        work_dir=work_dir,
        from_stage=4,
        scale_p1=p1_sfm,
        scale_p2=p2_sfm,
        scale_distance=1.00,
        viewer_scenes_dir=str(tmp_path / "scenes"),
    )

    # 4. Confirm Stage 3 was NOT rerun (trained output was reused)
    assert train_manifest.stat().st_mtime == stage3_mtime_before
    assert (work_dir / "preprocess").exists() is False

    # 5. Check Stage 4 Normalization output
    norm_manifest_path = work_dir / "normalize" / "normalization_manifest.json"
    assert norm_manifest_path.exists()
    with open(norm_manifest_path, "r") as f:
        norm_meta = json.load(f)

    # Scale factor applied must be 2.0
    assert np.isclose(norm_meta["scale_applied"], 2.0, rtol=1e-3)
    # Floor is at Y = 0 (bounds.min Y within 1e-6)
    assert abs(norm_meta["bounds"]["min"][1]) < 1e-6

    # 6. Check rescaled points distance:
    norm_ply = work_dir / "normalize" / "normalized_splat.ply"
    assert norm_ply.exists()
    v_cnt, props, offset = parse_ply_header(norm_ply.read_bytes()[:4096])
    type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
    dt_ply = np.dtype([(n, type_map.get(t, "<f4")) for n, t in props])
    with open(norm_ply, "rb") as f:
        f.seek(offset)
        transformed_pts = np.fromfile(f, dtype=dt_ply, count=v_cnt)

    p1_new = np.array([transformed_pts["x"][0], transformed_pts["y"][0], transformed_pts["z"][0]])
    p2_new = np.array([transformed_pts["x"][1], transformed_pts["y"][1], transformed_pts["z"][1]])

    rescaled_distance = float(np.linalg.norm(p1_new - p2_new))
    # Distance must equal real distance (1.00 m) within 1%
    assert np.isclose(rescaled_distance, 1.00, rtol=0.01)

    # Floor offset must have been computed AFTER scaling:
    # Original floor was at Y = -0.5. With scale_factor = 2.0, scaled floor is at Y = -1.0.
    # Therefore, floor translation must be +1.0 (so -1.0 + 1.0 = 0.0), NOT +0.5!
    assert np.isclose(norm_meta["floor_level_y"], -1.0, atol=0.05)
    # Both points were on the floor, so their new Y coordinates must be ~0.0
    assert np.isclose(p1_new[1], 0.0, atol=0.01)
    assert np.isclose(p2_new[1], 0.0, atol=0.01)



