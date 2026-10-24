"""Stage 4: Canonical coordinate frame normalization (RANSAC floor, +Y up, Y=0, metric scale)."""

from __future__ import annotations

import logging
import random
import struct
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    """Convert COLMAP quaternion [qw, qx, qy, qz] to 3x3 rotation matrix R (world to camera)."""
    qw, qx, qy, qz = qvec
    return np.array([
        [1 - 2 * qy**2 - 2 * qz**2, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw],
        [2 * qx * qy + 2 * qz * qw, 1 - 2 * qx**2 - 2 * qz**2, 2 * qy * qz - 2 * qx * qw],
        [2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx**2 - 2 * qy**2],
    ])


def rotmat2qvec(r: np.ndarray) -> np.ndarray:
    """Convert 3x3 rotation matrix R to unit quaternion [qw, qx, qy, qz]."""
    tr = r[0, 0] + r[1, 1] + r[2, 2]
    if tr > 0:
        s = 0.5 / np.sqrt(tr + 1.0)
        qw = 0.25 / s
        qx = (r[2, 1] - r[1, 2]) * s
        qy = (r[0, 2] - r[2, 0]) * s
        qz = (r[1, 0] - r[0, 1]) * s
    elif (r[0, 0] > r[1, 1]) and (r[0, 0] > r[2, 2]):
        s = 2.0 * np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
        qw = (r[2, 1] - r[1, 2]) / s
        qx = 0.25 * s
        qy = (r[0, 1] + r[1, 0]) / s
        qz = (r[0, 2] + r[2, 0]) / s
    elif r[1, 1] > r[2, 2]:
        s = 2.0 * np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
        qw = (r[0, 2] - r[2, 0]) / s
        qx = (r[0, 1] + r[1, 0]) / s
        qy = 0.25 * s
        qz = (r[1, 2] + r[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
        qw = (r[1, 0] - r[0, 1]) / s
        qx = (r[0, 2] + r[2, 0]) / s
        qy = (r[1, 2] + r[2, 1]) / s
        qz = 0.25 * s
    q = np.array([qw, qx, qy, qz])
    return q / np.linalg.norm(q)


def quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiply two quaternions [qw, qx, qy, qz]: q_out = q1 * q2."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def load_colmap_camera_poses(sparse_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load camera centers and camera up-vectors from COLMAP images.txt or images.bin.

    In COLMAP, world-to-camera is x_cam = R * x_world + t.
    Camera center in world: C = -R^T * t.
    Camera up vector in world: -R^T * [0, 1, 0] = -R[1, :] (since +Y is camera down).

    Args:
        sparse_dir: Directory containing images.bin or images.txt.

    Returns:
        Tuple of (camera_centers [M, 3], camera_up_vectors [M, 3]).

    Raises:
        FileNotFoundError: If neither images.txt nor images.bin exists.
        RuntimeError: If no camera poses could be parsed.
    """
    img_txt = sparse_dir / "images.txt"
    img_bin = sparse_dir / "images.bin"

    centers = []
    up_vectors = []

    if img_txt.exists():
        with open(img_txt, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        # Every alternate line contains: IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
        for i in range(0, len(lines), 2):
            parts = lines[i].split()
            if len(parts) >= 9:
                qvec = np.array([float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])])
                tvec = np.array([float(parts[5]), float(parts[6]), float(parts[7])])
                r = qvec2rotmat(qvec)
                c = -np.dot(r.T, tvec)
                up = -r[1, :]  # -R^T * [0, 1, 0]^T
                centers.append(c)
                up_vectors.append(up / np.linalg.norm(up))

    elif img_bin.exists():
        # Binary format for images.bin
        with open(img_bin, "rb") as f:
            num_images = struct.unpack("<Q", f.read(8))[0]
            for _ in range(num_images):
                f.read(4)  # image_id (uint32)
                qvec = np.array(struct.unpack("<dddd", f.read(32)))
                tvec = np.array(struct.unpack("<ddd", f.read(24)))
                f.read(4)  # camera_id (uint32)
                # read null-terminated name string
                while f.read(1) != b"\x00":
                    pass
                num_points2d = struct.unpack("<Q", f.read(8))[0]
                f.read(num_points2d * 24)  # x, y, point3d_id

                r = qvec2rotmat(qvec)
                c = -np.dot(r.T, tvec)
                up = -r[1, :]
                centers.append(c)
                up_vectors.append(up / np.linalg.norm(up))
    else:
        raise FileNotFoundError(f"Neither images.txt nor images.bin found in {sparse_dir}")

    if not centers:
        raise RuntimeError(f"No valid camera poses found in {sparse_dir}")

    return np.array(centers, dtype=np.float64), np.array(up_vectors, dtype=np.float64)


def fit_floor_plane_ransac(
    points: np.ndarray,
    camera_centers: np.ndarray | None = None,
    camera_up_vectors: np.ndarray | None = None,
    distance_threshold: float = 0.03,
    max_iterations: int = 3000,
    min_inliers: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit a dominant floor plane using RANSAC guided by camera up orientation.

    In an arbitrary COLMAP frame, candidate planes are checked against the mean camera up vector.
    A valid floor plane must:
    1. Have normal parallel to mean camera up vector (within 45 deg, dot product > 0.707).
    2. Lie BELOW the camera positions (mean camera position has positive signed distance to plane).
    3. Normal is flipped if necessary so it points upward towards the cameras.

    Args:
        points: (N, 3) array of 3D points.
        camera_centers: (M, 3) camera positions.
        camera_up_vectors: (M, 3) camera up vectors.
        distance_threshold: RANSAC inlier threshold (metres).
        max_iterations: Max RANSAC iterations.
        min_inliers: Minimum inliers required to accept floor.

    Returns:
        Tuple of (plane [a, b, c, d], inlier_indices).

    Raises:
        RuntimeError: If no candidate plane satisfies the geometric floor constraints.
    """
    n_points = points.shape[0]
    if n_points < 3:
        raise ValueError(f"At least 3 points required, got {n_points}")

    # Compute reference camera vectors if available
    if camera_centers is not None and len(camera_centers) > 0:
        c_mean = np.mean(camera_centers, axis=0)
    else:
        c_mean = np.mean(points, axis=0)

    if camera_up_vectors is not None and len(camera_up_vectors) > 0:
        u_mean = np.mean(camera_up_vectors, axis=0)
        u_mean = u_mean / np.linalg.norm(u_mean)
    else:
        u_mean = np.array([0.0, 1.0, 0.0])

    best_inliers: np.ndarray = np.array([], dtype=int)
    best_plane: np.ndarray | None = None

    for _ in range(max_iterations):
        sample_idx = random.sample(range(n_points), 3)
        p1, p2, p3 = points[sample_idx]

        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm < 1e-6:
            continue
        normal = normal / norm
        d = -np.dot(normal, p1)

        # Check alignment with camera up vector (within 45 degrees of parallel or anti-parallel)
        dot_u = np.dot(normal, u_mean)
        if abs(dot_u) < 0.7071:
            # Not perpendicular to gravity/vertical
            continue

        # Flip normal so it points upward towards camera up
        if dot_u < 0:
            normal = -normal
            d = -d

        # Check if cameras lie above the plane (signed distance > 0)
        if camera_centers is not None and len(camera_centers) > 0:
            dist_to_c = np.dot(normal, c_mean) + d
            if dist_to_c <= 0:
                # Plane is above the camera (e.g. ceiling plane)
                continue

        # Distance from all points to plane: |ax + by + cz + d|
        distances = np.abs(np.dot(points, normal) + d)
        inliers = np.where(distances < distance_threshold)[0]

        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_plane = np.append(normal, d)

    if best_plane is None or len(best_inliers) < min_inliers:
        raise RuntimeError(
            f"Floor plane detection failed: no valid floor plane found matching camera up orientation "
            f"(found {len(best_inliers)} inliers, minimum required {min_inliers})."
        )

    logger.info(
        "Floor plane fitted: [%.4f, %.4f, %.4f, %.4f] with %d inliers",
        best_plane[0], best_plane[1], best_plane[2], best_plane[3], len(best_inliers)
    )
    return best_plane, best_inliers


def compute_rotation_matrix_to_vector(
    source_vector: np.ndarray,
    target_vector: np.ndarray | None = None,
) -> np.ndarray:
    """Compute 3x3 rotation matrix R that rotates source_vector onto target_vector using Rodrigues formula."""
    if target_vector is None:
        target_vector = np.array([0.0, 1.0, 0.0])
    v_src = source_vector / np.linalg.norm(source_vector)
    v_tgt = target_vector / np.linalg.norm(target_vector)

    dot = float(np.dot(v_src, v_tgt))
    if np.isclose(dot, 1.0, atol=1e-6):
        return np.eye(3)
    if np.isclose(dot, -1.0, atol=1e-6):
        axis = np.array([1.0, 0.0, 0.0]) if not np.isclose(v_src[0], 1.0) else np.array([0.0, 0.0, 1.0])
        axis = axis - np.dot(axis, v_src) * v_src
        axis = axis / np.linalg.norm(axis)
        return 2.0 * np.outer(axis, axis) - np.eye(3)

    v = np.cross(v_src, v_tgt)
    s = np.linalg.norm(v)
    c = dot
    v_skew = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + v_skew + np.dot(v_skew, v_skew) * ((1.0 - c) / (s**2))


def compute_scale_factor(
    point1: list[float] | np.ndarray | None,
    point2: list[float] | np.ndarray | None,
    real_distance_m: float | None = 1.00,
) -> tuple[float, str, float | None]:
    """Compute metric scale factor from two clicked 3D points.

    If points are provided, returns (s_metric, "two_point_tape", None).
    If points are omitted or invalid, returns (1.0, "uncalibrated", None).

    Args:
        point1: 3D coordinates [x, y, z] of first point.
        point2: 3D coordinates [x, y, z] of second point.
        real_distance_m: Real measured distance in metres.

    Returns:
        Tuple of (scale_factor, scale_method, scale_error_pct).
    """
    if point1 is not None and point2 is not None and real_distance_m is not None:
        p1 = np.array(point1, dtype=np.float64)
        p2 = np.array(point2, dtype=np.float64)
        d_sfm = float(np.linalg.norm(p1 - p2))
        if d_sfm > 1e-4 and real_distance_m > 0:
            s_metric = float(real_distance_m / d_sfm)
            logger.info("Calibrated scale: %.4f (measured %.4f m from distance %.4f in SfM)", s_metric, real_distance_m, d_sfm)
            return s_metric, "two_point_tape", None

    logger.info("No scale calibration points provided; leaving scene in uncalibrated scale (1.0).")
    return 1.0, "uncalibrated", None


def normalize_scene(
    points: np.ndarray,
    camera_centers: np.ndarray | None = None,
    camera_up_vectors: np.ndarray | None = None,
    scale_factor: float = 1.0,
    distance_threshold: float = 0.03,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Normalize 3D points into canonical coordinate frame (+Y up, Y=0 floor, metric scale)."""
    # 1. Scale
    scaled_points = points * scale_factor

    # 2. Fit floor plane with camera orientation checks
    plane, inliers = fit_floor_plane_ransac(
        scaled_points,
        camera_centers=camera_centers * scale_factor if camera_centers is not None else None,
        camera_up_vectors=camera_up_vectors,
        distance_threshold=distance_threshold,
    )
    normal = plane[:3]

    # 3. Rotate normal to [0, 1, 0] (+Y up)
    r_mat = compute_rotation_matrix_to_vector(normal, np.array([0.0, 1.0, 0.0]))

    # Rotate all points
    rotated_points = np.dot(scaled_points, r_mat.T)

    # 4. Find floor level Y and translate so floor lies at Y = 0
    floor_inlier_y = rotated_points[inliers, 1]
    floor_y = float(np.median(floor_inlier_y))

    transformed_points = rotated_points.copy()
    transformed_points[:, 1] -= floor_y

    # Construct unified 4x4 matrix
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = r_mat * scale_factor
    transform_matrix[1, 3] = -floor_y

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
        "inlier_ratio": round(len(inliers) / len(points), 4),
    }

    return transformed_points, transform_matrix, metadata


def read_colmap_sparse_points(sparse_dir: Path) -> np.ndarray:
    """Read 3D points from COLMAP sparse reconstruction (points3D.txt or points3D.bin)."""
    txt_path = sparse_dir / "points3D.txt"
    bin_path = sparse_dir / "points3D.bin"
    if txt_path.exists():
        points = []
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    points.append([float(parts[1]), float(parts[2]), float(parts[3])])
        if points:
            return np.array(points, dtype=np.float32)
    elif bin_path.exists():
        points = []
        with open(bin_path, "rb") as f:
            num_points = struct.unpack("<Q", f.read(8))[0]
            for _ in range(num_points):
                _ = struct.unpack("<Q", f.read(8))[0]
                xyz = struct.unpack("<ddd", f.read(24))
                _ = f.read(3)
                _ = struct.unpack("<d", f.read(8))[0]
                track_len = struct.unpack("<Q", f.read(8))[0]
                f.seek(track_len * 8, 1)
                points.append(xyz)
        if points:
            return np.array(points, dtype=np.float32)
    raise FileNotFoundError(f"No COLMAP points3D found in {sparse_dir}")


def normalize_splat_ply(
    input_ply_path: str | Path,
    output_ply_path: str | Path,
    transform_matrix: np.ndarray,
    scale_factor: float = 1.0,
) -> None:
    """Apply 4x4 coordinate transformation matrix to a binary 3DGS PLY file.

    Updates positions, scales (log-space), and rotation quaternions.
    Preserves all colors, spherical harmonics, opacities, and headers.
    """
    from vytrix.optimize import parse_ply_header

    in_p = Path(input_ply_path)
    out_p = Path(output_ply_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with open(in_p, "rb") as f:
        file_bytes = f.read()

    vertex_count, properties, data_offset = parse_ply_header(file_bytes)
    type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
    dtype_fields = []
    for name, p_type in properties:
        np_type = type_map.get(p_type, "<f4")
        dtype_fields.append((name, np_type))

    dt = np.dtype(dtype_fields)
    vertex_data = np.frombuffer(file_bytes[data_offset:], dtype=dt, count=vertex_count).copy()

    # 1. Transform positions: x, y, z
    pos = np.stack([vertex_data["x"], vertex_data["y"], vertex_data["z"]], axis=-1)
    pos_h = np.hstack([pos, np.ones((vertex_count, 1), dtype=np.float64)])
    pos_trans = (pos_h @ transform_matrix.T)[:, :3]
    vertex_data["x"] = pos_trans[:, 0].astype(vertex_data["x"].dtype)
    vertex_data["y"] = pos_trans[:, 1].astype(vertex_data["y"].dtype)
    vertex_data["z"] = pos_trans[:, 2].astype(vertex_data["z"].dtype)

    # 2. Update scales if scale_factor != 1.0
    if not np.isclose(scale_factor, 1.0):
        log_s = np.log(scale_factor)
        if "scale_0" in vertex_data.dtype.names:
            vertex_data["scale_0"] = (vertex_data["scale_0"] + log_s).astype(vertex_data["scale_0"].dtype)
            vertex_data["scale_1"] = (vertex_data["scale_1"] + log_s).astype(vertex_data["scale_1"].dtype)
            vertex_data["scale_2"] = (vertex_data["scale_2"] + log_s).astype(vertex_data["scale_2"].dtype)

    # 3. Rotate quaternions
    rot_matrix = transform_matrix[:3, :3] / scale_factor
    q_rot = rotmat2qvec(rot_matrix)
    if "rot_0" in vertex_data.dtype.names:
        w1, x1, y1, z1 = q_rot
        w2 = vertex_data["rot_0"].astype(np.float64)
        x2 = vertex_data["rot_1"].astype(np.float64)
        y2 = vertex_data["rot_2"].astype(np.float64)
        z2 = vertex_data["rot_3"].astype(np.float64)

        w_out = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        x_out = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y_out = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z_out = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2

        norms = np.sqrt(w_out**2 + x_out**2 + y_out**2 + z_out**2) + 1e-8
        vertex_data["rot_0"] = (w_out / norms).astype(vertex_data["rot_0"].dtype)
        vertex_data["rot_1"] = (x_out / norms).astype(vertex_data["rot_1"].dtype)
        vertex_data["rot_2"] = (y_out / norms).astype(vertex_data["rot_2"].dtype)
        vertex_data["rot_3"] = (z_out / norms).astype(vertex_data["rot_3"].dtype)

    header_bytes = file_bytes[:data_offset]
    with open(out_p, "wb") as f:
        f.write(header_bytes)
        f.write(vertex_data.tobytes())


# Backwards compatibility alias for existing tests
fit_plane_ransac = fit_floor_plane_ransac
