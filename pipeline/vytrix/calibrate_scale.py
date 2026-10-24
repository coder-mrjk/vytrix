"""CLI helper tool to calibrate metric scale from two picked 3D points.

Calculates scale factor s = d_real / ||p1 - p2|| and outputs CLI flags
for the VYTRIX reconstruction pipeline.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def parse_coords(val: str) -> list[float]:
    """Parse comma-separated 'x,y,z' string into list of 3 floats."""
    parts = [float(x.strip()) for x in val.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Expected 3 coordinates (x,y,z), got {len(parts)} in '{val}'")
    return parts


def compute_calibration(
    p1: list[float],
    p2: list[float],
    real_distance_m: float = 1.00,
) -> dict[str, float | str | list[float]]:
    """Compute Euclidean distance in model and resulting metric scale factor."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    d_sfm = math.sqrt(dx * dx + dy * dy + dz * dz)

    if d_sfm < 1e-5:
        raise ValueError("Selected points are virtually identical (distance < 1e-5 m).")
    if real_distance_m <= 0:
        raise ValueError(f"Real distance must be positive, got {real_distance_m}")

    scale_factor = real_distance_m / d_sfm
    scale_points_str = f"{p1[0]:.4f},{p1[1]:.4f},{p1[2]:.4f},{p2[0]:.4f},{p2[1]:.4f},{p2[2]:.4f}"

    return {
        "point1": p1,
        "point2": p2,
        "model_distance_sfm": round(d_sfm, 4),
        "real_distance_m": round(real_distance_m, 4),
        "scale_factor": round(scale_factor, 6),
        "cli_flag": f"--scale-points {scale_points_str} --scale-distance {real_distance_m:.2f}",
        "scale_method": "two_point_tape",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="VYTRIX Two-Point Metric Scale Calibration Helper")
    parser.add_argument("--p1", type=str, default=None, help="Coordinates of first point 'x,y,z'")
    parser.add_argument("--p2", type=str, default=None, help="Coordinates of second point 'x,y,z'")
    parser.add_argument("--points", type=str, default=None, help="Comma-separated 6 coordinates 'x1,y1,z1,x2,y2,z2'")
    parser.add_argument("--real-distance", type=float, default=1.00, help="Real measured distance in metres (default: 1.00)")
    parser.add_argument("--update-meta", type=str, default=None, help="Optional path to capture_meta.json to update")

    args = parser.parse_args()

    p1: list[float] | None = None
    p2: list[float] | None = None

    if args.points:
        coords = [float(x.strip()) for x in args.points.split(",")]
        if len(coords) != 6:
            sys.exit(f"Error: --points requires 6 values (x1,y1,z1,x2,y2,z2), got {len(coords)}")
        p1 = coords[:3]
        p2 = coords[3:]
    elif args.p1 and args.p2:
        p1 = parse_coords(args.p1)
        p2 = parse_coords(args.p2)
    else:
        # Interactive prompt
        print("==================================================")
        print("   VYTRIX Interactive Scale Calibration Helper    ")
        print("==================================================")
        print("Tip: Get coordinates by pressing 'P' in the VYTRIX web viewer.\n")
        try:
            p1_str = input("Enter Point 1 (x, y, z): ").strip()
            p2_str = input("Enter Point 2 (x, y, z): ").strip()
            p1 = parse_coords(p1_str)
            p2 = parse_coords(p2_str)
            dist_str = input("Enter real-world distance in metres [1.00]: ").strip()
            if dist_str:
                args.real_distance = float(dist_str)
        except (ValueError, KeyboardInterrupt) as e:
            sys.exit(f"Aborted: {e}")

    try:
        res = compute_calibration(p1, p2, args.real_distance)
    except ValueError as e:
        sys.exit(f"Calibration Error: {e}")

    print("\n---------------- Calibration Result ----------------")
    print(f"Point 1:           {res['point1']}")
    print(f"Point 2:           {res['point2']}")
    print(f"SfM Model Distance: {res['model_distance_sfm']:.4f} units")
    print(f"Real Distance:     {res['real_distance_m']:.4f} m")
    print(f"Scale Factor:      {res['scale_factor']:.6f}x")
    print("\nPipeline CLI Flags:")
    print(f"  {res['cli_flag']}")
    print("----------------------------------------------------\n")

    if args.update_meta:
        meta_path = Path(args.update_meta)
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["scale_reference"] = {
                "type": "measured_floor_tape",
                "distance_meters": res["real_distance_m"],
                "calibrated_points": [res["point1"], res["point2"]],
                "scale_factor": res["scale_factor"],
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            print(f"Updated scale reference in {meta_path}")


if __name__ == "__main__":
    main()
