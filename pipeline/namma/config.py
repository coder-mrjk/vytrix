"""Configuration loader and validator for VYTRIX pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: str | Path = "config.yaml") -> Dict[str, Any]:
    """Load and validate pipeline configuration YAML file.

    Args:
        config_path: Path to config.yaml file.

    Returns:
        Dict containing verified configuration parameters.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        ValueError: If mandatory configuration sections are missing.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f) or {}

    required_sections = ["scene", "capture", "preprocess", "sfm", "training", "normalization"]
    missing = [sec for sec in required_sections if sec not in config]
    if missing:
        raise ValueError(f"Missing required configuration sections in {path}: {missing}")

    logger.info("Successfully loaded and validated configuration from %s", path)
    return config
