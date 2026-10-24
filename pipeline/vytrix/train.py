"""Stage 3: 3D Gaussian Splatting training on Colab GPU with Google Drive checkpoints.

Uses gsplat reference simple_trainer.py.
TODO(verify): Verify CLI flags and exact gsplat release on first Google Colab GPU run.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_trainer_eval_metrics(output_text: str) -> dict[str, float | None]:
    """Parse real PSNR and SSIM from trainer evaluation logs if evaluated.

    Args:
        output_text: Console output from simple_trainer.py.

    Returns:
        Dict with "psnr" and "ssim", or None if evaluation was not performed.
    """
    psnr_match = re.search(r"(?:Mean\s+)?PSNR:\s*([0-9.]+)", output_text, re.IGNORECASE)
    ssim_match = re.search(r"(?:Mean\s+)?SSIM:\s*([0-9.]+)", output_text, re.IGNORECASE)

    psnr = float(psnr_match.group(1)) if psnr_match else None
    ssim = float(ssim_match.group(1)) if ssim_match else None
    return {"psnr": psnr, "ssim": ssim}


def train_gaussian_splat(
    data_dir: str | Path,
    output_dir: str | Path,
    trainer_script: str | Path = "/content/gsplat_src/examples/simple_trainer.py",
    iterations: int = 15000,
    eval_steps: int = -1,
    sh_degree: int = 3,
    drive_checkpoint_dir: str | None = None,
) -> dict[str, Any]:
    """Train 3D Gaussian Splatting model on GPU and checkpoint to Google Drive.

    Args:
        data_dir: Directory containing COLMAP sparse model and images.
        output_dir: Output directory where trained model checkpoints and ply will be written.
        trainer_script: Path to gsplat simple_trainer.py script.
        iterations: Number of training optimization iterations.
        eval_steps: Step interval to evaluate test views (-1 disables eval during training).
        sh_degree: Spherical Harmonics degree.
        drive_checkpoint_dir: Path to Google Drive directory for persistent checkpoints.

    Returns:
        Dict containing real training elapsed time, iterations, measured PSNR/SSIM (or null), and output ply path.

    Raises:
        FileNotFoundError: If data_dir or trainer script does not exist.
        RuntimeError: If training fails or fails to generate a valid non-empty point_cloud.ply.
    """
    data_path = Path(data_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not data_path.exists():
        raise FileNotFoundError(f"COLMAP data directory not found at: {data_path.resolve()}")

    t_script = Path(trainer_script)
    # Check if local fallback or Colab path exists
    if not t_script.exists():
        local_cand = Path("gsplat/examples/simple_trainer.py")
        if local_cand.exists():
            t_script = local_cand
        else:
            raise FileNotFoundError(
                f"gsplat simple_trainer.py not found at {t_script}. "
                "Ensure gsplat repository is cloned per Colab notebook instructions."
            )

    start_time = time.time()
    logger.info("Starting 3D Gaussian Splatting training for %d iterations", iterations)

    # Command invocation for gsplat reference simple_trainer.py
    # TODO(verify): Validate CLI flags against gsplat release on Colab
    cmd = [
        "python",
        str(t_script),
        "default",
        "--data_dir",
        str(data_path),
        "--data_factor",
        "1",
        "--result_dir",
        str(out_path),
        "--max_steps",
        str(iterations),
        "--save_ply",
        "--ply_steps",
        str(iterations),
        "--eval_steps",
        str(eval_steps),
    ]

    logger.info("Executing training command: %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    combined_log = proc.stdout + "\n" + proc.stderr

    if proc.returncode != 0:
        raise RuntimeError(
            f"gsplat training failed with return code {proc.returncode}:\n{combined_log}"
        )

    # Locate generated point_cloud.ply
    ply_candidates = [
        out_path / "ply" / f"point_cloud_{iterations}.ply",
        out_path / "point_cloud.ply",
        out_path / "ply" / "point_cloud.ply",
    ]

    found_ply = None
    for cand in ply_candidates:
        if cand.exists() and cand.stat().st_size > 1000:
            found_ply = cand
            break

    if not found_ply:
        raise RuntimeError(
            f"gsplat training finished but no valid point_cloud.ply was found in {out_path}.\n"
            f"Trainer logs:\n{combined_log[-1000:]}"
        )

    # Copy to canonical splat_raw.ply
    raw_ply = out_path / "splat_raw.ply"
    shutil.copy2(found_ply, raw_ply)

    # Parse real evaluation metrics if available, otherwise strictly null
    eval_metrics = parse_trainer_eval_metrics(combined_log)
    elapsed = time.time() - start_time

    # Persistent Drive backup if configured
    if drive_checkpoint_dir and os.path.exists(drive_checkpoint_dir):
        logger.info("Backing up model outputs to Google Drive: %s", drive_checkpoint_dir)
        drive_dest = Path(drive_checkpoint_dir)
        drive_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raw_ply, drive_dest / raw_ply.name)

    metrics = {
        "stage": "train",
        "iterations": iterations,
        "sh_degree": sh_degree,
        "elapsed_seconds": round(elapsed, 2),
        "psnr": eval_metrics["psnr"],
        "ssim": eval_metrics["ssim"],
        "raw_ply_file": str(raw_ply.resolve()),
        "raw_ply_bytes": raw_ply.stat().st_size,
    }

    metrics_file = out_path / "train_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Training complete in %.2fs. Outputs saved to %s", elapsed, raw_ply)
    return metrics
