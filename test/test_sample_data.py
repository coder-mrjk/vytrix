"""Tests validating sample dataset integrity and format in test/data/."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
from vytrix.normalize import compute_scale_factor, fit_plane_ransac


def test_sample_splat_binary_structure():
    """Verify that sample splat has valid 32-byte Gaussian headers and expected count."""
    splat_file = Path("test/data/scene.splat")
    assert splat_file.exists(), "test/data/scene.splat missing!"

    file_size = splat_file.stat().st_size
    assert file_size % 32 == 0, "Splat file size must be an exact multiple of 32 bytes!"

    num_gaussians = file_size // 32
    assert num_gaussians == 6680, f"Expected 6,680 Gaussians, found {num_gaussians}"

    # Read first 100 Gaussians and verify values are finite
    with open(splat_file, "rb") as f:
        data = f.read(100 * 32)

    for i in range(100):
        chunk = data[i * 32 : (i + 1) * 32]
        pos = struct.unpack("<fff", chunk[0:12])
        scales = struct.unpack("<fff", chunk[12:24])
        colors = struct.unpack("<BBBB", chunk[24:28])

        assert all(np.isfinite(pos)), f"Gaussian {i} position has non-finite values"
        assert all(s > 0 for s in scales), f"Gaussian {i} scales must be positive"
        assert all(0 <= c <= 255 for c in colors), f"Gaussian {i} colors must be in [0, 255]"


def test_sample_capture_meta():
    """Verify that sample capture metadata conforms to VYTRIX scale calibration specs."""
    meta_file = Path("test/data/capture_meta.json")
    assert meta_file.exists(), "test/data/capture_meta.json missing!"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["scale_reference"]["distance_meters"] == 1.00
    assert meta["scale_reference"]["type"] == "measured_floor_tape"

    # Verify uncalibrated fallback when points are not yet measured in SfM
    s_factor, method, err = compute_scale_factor(None, None, meta["scale_reference"]["distance_meters"])
    assert s_factor == 1.0
    assert method == "uncalibrated"
    assert err is None

    # Verify two-point calibration when SfM coordinates are provided
    p1 = [0.0, 0.0, 0.0]
    p2 = [0.5, 0.0, 0.0]
    s_cal, method_cal, _ = compute_scale_factor(p1, p2, 1.00)
    assert np.isclose(s_cal, 2.0)
    assert method_cal == "two_point_tape"


def test_sample_splat_plane_fitting():
    """Verify that RANSAC plane fitting on sample floor Gaussians detects ground plane."""
    splat_file = Path("test/data/scene.splat")
    with open(splat_file, "rb") as f:
        raw_bytes = f.read()

    num_gaussians = len(raw_bytes) // 32
    positions = np.zeros((num_gaussians, 3), dtype=np.float32)

    for i in range(num_gaussians):
        positions[i] = struct.unpack("<fff", raw_bytes[i * 32 : i * 32 + 12])

    # Fit ground plane
    plane, inliers = fit_plane_ransac(positions, distance_threshold=0.05, max_iterations=500)
    normal = plane[:3]

    # Dominant floor plane has upward normal [0, 1, 0]
    assert np.isclose(np.abs(normal[1]), 1.0, atol=0.15)
    assert len(inliers) >= 1500
