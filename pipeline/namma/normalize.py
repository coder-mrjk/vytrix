"""Stage 4: Canonical coordinate frame normalization (RANSAC floor, +Y up, Y=0, metric scale)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def fit_plane_ransac(
    points: np.ndarray,
    distance_threshold: float = 0.03,
    max_iterations: int = 2000,
) -> Tuple[np.ndarray, np.ndarray]:
    """Fit a dominant 3D plane using RANSAC.

    Args:
        points: (N, 3) numpy array of 3D points.
        distance_threshold: Distance threshold (metres) to classify inliers.
        max_iterations: Maximum number of RANSAC iterations.

    Returns:
        Tuple of (plane_equation [a, b, c, d], inlier_indices).
        Plane equation satisfies ax + by + cz + d = 0 with normal [a, b, c] normalized.
    """
    n_points = points.shape[0]
    if n_points < 3:
        raise ValueError("At least 3 points required to fit a 3D plane.")

    best_inliers: np.ndarray = np.array([], dtype=int)
    best_plane: np.ndarray = np.array([0.0, 1.0, 0.0, 0.0])

    for _ in range(max_iterations):
        sample_idx = np.random.choice(n_points, 3, replace=False)
        p1, p2, p3 = points[sample_idx]

        # Normal vector via cross product
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm < 1e-6:
            continue
        normal = normal / norm

        d = -np.dot(normal, p1)

        # Distance from all points to plane: |ax + by + cz + d|
        distances = np.abs(np.dot(points, normal) + d)
        inliers = np.where(distances < distance_threshold)[0]

        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_plane = np.append(normal, d)

    # Ensure normal points upwards (positive dot product with approx up)
    if best_plane[1] < 0:
        best_plane = -best_plane

    logger.info(
        "RANSAC fitted plane: [%.4f, %.4f, %.4f, %.4f] with %d inliers (%.1f%%)",
        best_plane[0],
        best_plane[1],
        best_plane[2],
        best_plane[3],
        len(best_inliers),
        (len(best_inliers) / n_points) * 100,
    )
    return best_plane, best_inliers


def compute_rotation_matrix_to_vector(
    source_vector: np.ndarray,
    target_vector: np.ndarray = np.array([0.0, 1.0, 0.0]),
) -> np.ndarray:
    """Compute 3x3 rotation matrix that rotates source_vector onto target_vector.

    Uses Rodrigues' rotation formula.

    Args:
        source_vector: Unit normal vector of source plane.
        target_vector: Unit normal vector of target axis (default: [0, 1, 0] for +Y up).

    Returns:
        3x3 orthogonal rotation matrix R.
    """
    v_src = source_vector / np.linalg.norm(source_vector)
    v_tgt = target_vector / np.linalg.norm(target_vector)

    dot = np.dot(v_src, v_tgt)
    if np.isclose(dot, 1.0):
        return np.eye(3)
    if np.isclose(dot, -1.0):
        # 180 degree rotation around arbitrary orthogonal vector
        axis = np.array([1.0, 0.0, 0.0]) if not np.isclose(v_src[0], 1.0) else np.array([0.0, 0.0, 1.0])
        axis = axis - np.dot(axis, v_src) * v_src
        axis = axis / np.linalg.norm(axis)
        return 2.0 * np.outer(axis, axis) - np.eye(3)

    v = np.cross(v_src, v_tgt)
    s = np.linalg.norm(v)
    c = dot

    # Skew-symmetric cross-product matrix of v
    v_skew = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])

    r = np.eye(3) + v_skew + np.dot(v_skew, v_skew) * ((1.0 - c) / (s**2))
    return r


def normalize_scene(
    points: np.ndarray,
    scale_factor: float = 1.0,
    distance_threshold: float = 0.03,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Normalize 3D points into canonical coordinate frame:

    - Gravity aligned (+Y = up).
    - Floor plane at Y = 0.
    - Metrically scaled (units in metres).
    - Floater outlier bounds calculated.

    Args:
        points: (N, 3) numpy array of 3D points.
        scale_factor: Multiplier to convert SfM arbitrary units into real-world metres.
        distance_threshold: RANSAC threshold.

    Returns:
        Tuple of (transformed_points, 4x4 transform_matrix, metadata_dict).
    """
    # 1. Scale
    scaled_points = points * scale_factor

    # 2. Fit ground plane via RANSAC
    plane, inliers = fit_plane_ransac(scaled_points, distance_threshold=distance_threshold)
    normal = plane[:3]
    d = plane[3]

    # 3. Rotate normal to [0, 1, 0]
    r_mat = compute_rotation_matrix_to_vector(normal, np.array([0.0, 1.0, 0.0]))

    # Rotate all points
    rotated_points = np.dot(scaled_points, r_mat.T)

    # 4. Find floor Y coordinate in rotated space and translate so floor Y = 0
    floor_inlier_y = rotated_points[inliers, 1]
    floor_y = float(np.median(floor_inlier_y))

    transformed_points = rotated_points.copy()
    transformed_points[:, 1] -= floor_y

    # Construct unified 4x4 affine transformation matrix
    # T = Translation(-floor_y) * Rotation * Scale
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = r_mat * scale_factor
    transform_matrix[1, 3] = -floor_y

    # 5. Compute robust 1st-99th percentile bounds
    p_low = np.percentile(transformed_points, 1.0, axis=0)
    p_high = np.percentile(transformed_points, 99.0, axis=0)

    bounds = {
        "min": [round(float(p_low[0]), 2), 0.0, round(float(p_low[2]), 2)],
        "max": [round(float(p_high[0]), 2), round(float(p_high[1]), 2), round(float(p_high[2]), 2)],
    }

    metadata = {
        "scale_applied": scale_factor,
        "floor_plane_original": [round(float(x), 4) for x in plane],
        "floor_level_y": round(floor_y, 4),
        "bounds": bounds,
        "spawn_position": [0.0, 0.0, 0.0],
        "eye_height_m": 1.6,
        "inlier_ratio": round(len(inliers) / len(points), 3),
    }

    return transformed_points, transform_matrix, metadata
