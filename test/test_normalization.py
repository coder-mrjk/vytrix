"""Unit tests for geometry and scene normalization mathematics in VYTRIX."""

from __future__ import annotations

import numpy as np
from vytrix.normalize import (
    compute_rotation_matrix_to_vector,
    fit_plane_ransac,
    normalize_scene,
)


def test_compute_rotation_matrix_identity():
    """Verify that rotation between identical vectors yields the 3x3 identity matrix."""
    v = np.array([0.0, 1.0, 0.0])
    r = compute_rotation_matrix_to_vector(v, v)
    np.testing.assert_allclose(r, np.eye(3), atol=1e-6)


def test_compute_rotation_matrix_orthogonality():
    """Verify that rotation matrix is strictly orthogonal (R.T @ R == I, det(R) == 1)."""
    # Vector tilted 45 degrees between Y and Z
    source = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)
    target = np.array([0.0, 1.0, 0.0])

    r = compute_rotation_matrix_to_vector(source, target)

    # Orthogonality check
    np.testing.assert_allclose(np.dot(r.T, r), np.eye(3), atol=1e-6)
    # Proper rotation (determinant = +1)
    assert np.isclose(np.linalg.det(r), 1.0, atol=1e-6)

    # Transform source vector
    rotated = np.dot(r, source)
    np.testing.assert_allclose(rotated, target, atol=1e-6)


def test_fit_plane_ransac_synthetic():
    """Verify RANSAC ground plane fitting on a synthetic horizontal floor plane with noise."""
    np.random.seed(42)
    n_inliers = 500
    n_outliers = 100

    # Inliers on horizontal plane Y = 0.5 with Gaussian noise
    inliers = np.zeros((n_inliers, 3))
    inliers[:, 0] = np.random.uniform(-5, 5, n_inliers)
    inliers[:, 2] = np.random.uniform(-5, 5, n_inliers)
    inliers[:, 1] = 0.5 + np.random.normal(0, 0.005, n_inliers)

    # Outliers scattered randomly
    outliers = np.random.uniform(-5, 5, (n_outliers, 3))

    points = np.vstack([inliers, outliers])
    plane, inlier_indices = fit_plane_ransac(points, distance_threshold=0.03, max_iterations=1000)

    # Normal should be close to [0, 1, 0]
    normal = plane[:3]
    np.testing.assert_allclose(np.abs(normal), np.array([0.0, 1.0, 0.0]), atol=0.05)
    # Number of inliers should capture majority of the true inliers
    assert len(inlier_indices) >= n_inliers * 0.90


def test_normalize_scene_canonical_leveling():
    """Verify that normalize_scene aligns ground plane to Y=0 and preserves metric scale."""
    np.random.seed(123)
    # Create tilted floor plane
    n_pts = 400
    pts = np.zeros((n_pts, 3))
    pts[:, 0] = np.random.uniform(-2, 2, n_pts)
    pts[:, 2] = np.random.uniform(-2, 2, n_pts)
    # Floor tilted slightly around X axis
    tilt_angle = np.radians(15.0)
    pts[:, 1] = pts[:, 2] * np.tan(tilt_angle) + 1.2  # Floor height at 1.2

    transformed, _matrix, meta = normalize_scene(pts, scale_factor=2.0, distance_threshold=0.05)

    # In transformed space, floor median Y must be approx 0.0
    floor_median_y = np.median(transformed[:, 1])
    assert np.isclose(floor_median_y, 0.0, atol=0.05)

    # Check bounds min Y is >= 0
    assert meta["bounds"]["min"][1] == 0.0
    assert meta["eye_height_m"] == 1.6
