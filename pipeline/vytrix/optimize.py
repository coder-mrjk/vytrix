"""Stage 5: Splat pruning and web format conversion (.ply -> .splat).

Converts 3D Gaussian Splatting PLY point clouds into standard 32-byte binary .splat format.
Each Gaussian is packed as:
- Position (X, Y, Z): 3 x float32 (12 bytes)
- Scale (Sx, Sy, Sz): 3 x float32 (12 bytes)
- Color (R, G, B, A): 4 x uint8 (4 bytes) - SH DC to RGB conversion; Alpha = sigmoid(opacity) * 255
- Rotation (rot_0, rot_1, rot_2, rot_3): 4 x uint8 (4 bytes)
Total: exactly 32 bytes per Gaussian.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Spherical Harmonics DC constant: Y_0^0 = 1 / (2 * sqrt(pi))
SH_C0: float = 0.28209479177387814


def parse_ply_header(file_bytes: bytes) -> tuple[int, list[tuple[str, str]], int]:
    """Parse ASCII header of binary little-endian PLY file.

    Returns:
        Tuple of (vertex_count, properties_list, data_offset).
    """
    header_end = file_bytes.find(b"end_header\n")
    if header_end == -1:
        # Check Windows CRLF
        header_end = file_bytes.find(b"end_header\r\n")
        if header_end == -1:
            raise ValueError("Invalid PLY file: 'end_header' token not found.")
        end_offset = header_end + len(b"end_header\r\n")
    else:
        end_offset = header_end + len(b"end_header\n")

    header_text = file_bytes[:header_end].decode("ascii", errors="ignore")
    lines = header_text.splitlines()

    vertex_count = 0
    properties: list[tuple[str, str]] = []

    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        if parts[0] == "element" and len(parts) >= 3 and parts[1] == "vertex":
            vertex_count = int(parts[2])
        elif parts[0] == "property" and len(parts) >= 3:
            prop_type = parts[1]
            prop_name = parts[2]
            properties.append((prop_name, prop_type))

    if vertex_count <= 0:
        raise ValueError(f"PLY header specifies non-positive vertex count: {vertex_count}")

    return vertex_count, properties, end_offset


def convert_ply_to_splat(
    input_ply_path: str | Path,
    output_splat_path: str | Path,
    opacity_threshold: float = 0.05,
) -> dict[str, Any]:
    """Read binary 3DGS PLY file, prune low-opacity floaters, and write standard 32-byte .splat.

    Args:
        input_ply_path: Path to input 3D Gaussian Splat PLY.
        output_splat_path: Path to target .splat output file.
        opacity_threshold: Sigmoid alpha threshold (0.0 to 1.0) below which splats are pruned.

    Returns:
        Dictionary containing real initial/pruned Gaussian counts and byte sizes.

    Raises:
        FileNotFoundError: If input PLY does not exist.
        RuntimeError: If all Gaussians are pruned or file is corrupted.
    """
    in_path = Path(input_ply_path)
    out_path = Path(output_splat_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(f"Input PLY file not found: {in_path.resolve()}")

    start_time = time.time()
    file_size_bytes = in_path.stat().st_size
    if file_size_bytes == 0:
        raise RuntimeError(f"Input PLY file is empty (0 bytes): {in_path}")

    with open(in_path, "rb") as f:
        file_bytes = f.read()

    vertex_count, properties, data_offset = parse_ply_header(file_bytes)
    prop_names = [name for name, _ in properties]

    # Required 3DGS properties
    required_props = ["x", "y", "z", "opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    for rp in required_props:
        if rp not in prop_names:
            raise ValueError(f"Input PLY missing required 3DGS property: '{rp}'")

    # Build numpy dtype (assume standard 4-byte float for 3DGS PLY properties)
    type_map = {"float": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1", "int": "<i4"}
    dtype_fields = []
    for name, p_type in properties:
        np_type = type_map.get(p_type, "<f4")
        dtype_fields.append((name, np_type))

    dt = np.dtype(dtype_fields)
    vertex_data = np.frombuffer(file_bytes[data_offset:], dtype=dt, count=vertex_count)

    # 1. Opacity Pruning: alpha = sigmoid(opacity) * 255
    raw_opacity = vertex_data["opacity"].astype(np.float64)
    alpha_float = 1.0 / (1.0 + np.exp(-raw_opacity))
    mask = alpha_float >= opacity_threshold
    pruned_count = int(np.sum(mask))

    if pruned_count == 0:
        raise RuntimeError(
            f"All {vertex_count} Gaussians were pruned by opacity threshold {opacity_threshold}."
        )

    filtered = vertex_data[mask]
    alpha_bytes = np.clip(alpha_float[mask] * 255.0, 0, 255).astype(np.uint8)

    # 2. Position (float32)
    pos_x = filtered["x"].astype(np.float32)
    pos_y = filtered["y"].astype(np.float32)
    pos_z = filtered["z"].astype(np.float32)

    # 3. Scales: linear scale = exp(scale_i)
    sc_x = np.exp(filtered["scale_0"].astype(np.float64)).astype(np.float32)
    sc_y = np.exp(filtered["scale_1"].astype(np.float64)).astype(np.float32)
    sc_z = np.exp(filtered["scale_2"].astype(np.float64)).astype(np.float32)

    # 4. Color: SH DC to RGB conversion
    if "f_dc_0" in prop_names and "f_dc_1" in prop_names and "f_dc_2" in prop_names:
        r_f = 0.5 + SH_C0 * filtered["f_dc_0"].astype(np.float64)
        g_f = 0.5 + SH_C0 * filtered["f_dc_1"].astype(np.float64)
        b_f = 0.5 + SH_C0 * filtered["f_dc_2"].astype(np.float64)
        r_bytes = np.clip(r_f * 255.0, 0, 255).astype(np.uint8)
        g_bytes = np.clip(g_f * 255.0, 0, 255).astype(np.uint8)
        b_bytes = np.clip(b_f * 255.0, 0, 255).astype(np.uint8)
    else:
        # Fallback to direct vertex colors if present
        r_bytes = filtered["red"].astype(np.uint8) if "red" in prop_names else np.full(pruned_count, 200, dtype=np.uint8)
        g_bytes = filtered["green"].astype(np.uint8) if "green" in prop_names else np.full(pruned_count, 200, dtype=np.uint8)
        b_bytes = filtered["blue"].astype(np.uint8) if "blue" in prop_names else np.full(pruned_count, 200, dtype=np.uint8)

    # 5. Quaternion Rotations: [rot_0, rot_1, rot_2, rot_3] = [w, x, y, z]
    q0 = filtered["rot_0"].astype(np.float64)
    q1 = filtered["rot_1"].astype(np.float64)
    q2 = filtered["rot_2"].astype(np.float64)
    q3 = filtered["rot_3"].astype(np.float64)
    q_norm = np.sqrt(q0**2 + q1**2 + q2**2 + q3**2) + 1e-8
    q0, q1, q2, q3 = q0 / q_norm, q1 / q_norm, q2 / q_norm, q3 / q_norm

    # Map quaternion [-1.0, 1.0] -> [0, 255] uint8
    r0 = np.clip(q0 * 128.0 + 128.0, 0, 255).astype(np.uint8)
    r1 = np.clip(q1 * 128.0 + 128.0, 0, 255).astype(np.uint8)
    r2 = np.clip(q2 * 128.0 + 128.0, 0, 255).astype(np.uint8)
    r3 = np.clip(q3 * 128.0 + 128.0, 0, 255).astype(np.uint8)

    # 6. Assemble into contiguous structured binary array (32 bytes per Gaussian)
    splat_dtype = np.dtype([
        ("pos", "<f4", (3,)),
        ("scale", "<f4", (3,)),
        ("color", "u1", (4,)),
        ("rot", "u1", (4,)),
    ])
    assert splat_dtype.itemsize == 32, f"Expected 32 bytes per Gaussian, got {splat_dtype.itemsize}"

    splat_array = np.empty(pruned_count, dtype=splat_dtype)
    splat_array["pos"][:, 0] = pos_x
    splat_array["pos"][:, 1] = pos_y
    splat_array["pos"][:, 2] = pos_z

    splat_array["scale"][:, 0] = sc_x
    splat_array["scale"][:, 1] = sc_y
    splat_array["scale"][:, 2] = sc_z

    splat_array["color"][:, 0] = r_bytes
    splat_array["color"][:, 1] = g_bytes
    splat_array["color"][:, 2] = b_bytes
    splat_array["color"][:, 3] = alpha_bytes

    splat_array["rot"][:, 0] = r0
    splat_array["rot"][:, 1] = r1
    splat_array["rot"][:, 2] = r2
    splat_array["rot"][:, 3] = r3

    with open(out_path, "wb") as f:
        f.write(splat_array.tobytes())

    final_size_bytes = out_path.stat().st_size
    assert final_size_bytes == pruned_count * 32, (
        f"Output size mismatch: expected {pruned_count * 32} bytes, got {final_size_bytes}"
    )

    elapsed = time.time() - start_time
    compression_ratio = round(file_size_bytes / max(1, final_size_bytes), 2)

    logger.info(
        "Converted %s -> %s: %d Gaussians (%d pruned, %.1f%% kept), %.2f MB -> %.2f MB in %.2fs",
        in_path.name,
        out_path.name,
        pruned_count,
        vertex_count - pruned_count,
        (pruned_count / vertex_count) * 100,
        file_size_bytes / (1024 * 1024),
        final_size_bytes / (1024 * 1024),
        elapsed,
    )

    return {
        "stage": "optimize",
        "input_file": str(in_path.name),
        "output_file": str(out_path.name),
        "format": "splat",
        "initial_bytes": file_size_bytes,
        "final_bytes": final_size_bytes,
        "compression_ratio": f"{compression_ratio}:1",
        "initial_gaussians": vertex_count,
        "pruned_gaussians": pruned_count,
        "elapsed_seconds": round(elapsed, 2),
    }


def compress_and_optimize_splat(
    input_ply_path: str | Path,
    output_dir: str | Path,
    opacity_threshold: float = 0.05,
    export_format: str = "splat",
) -> dict[str, Any]:
    """Stage 5 entrypoint: converts input PLY to web splat and writes manifest."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_file = out_dir / "scene.splat"

    manifest = convert_ply_to_splat(
        input_ply_path=input_ply_path,
        output_splat_path=target_file,
        opacity_threshold=opacity_threshold,
    )

    metrics_file = out_dir / "optimize_manifest.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
