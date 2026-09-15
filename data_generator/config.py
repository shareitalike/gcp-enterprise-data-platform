"""
config.py — configuration loader for Commerce360 pipelines.

Loads the appropriate config.yaml for the current environment.
Environment is determined by the C360_ENV environment variable:
  - local          → configs/local/config.yaml
  - ingestion-dev  → configs/ingestion-dev/config.yaml
  - analytics-dev  → configs/analytics-dev/config.yaml

Usage:
    from data_generator.config import load_config
    cfg = load_config()
    seed = cfg["data_generator"]["seed"]
"""

import os
import yaml
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent
_VALID_ENVS = {"local", "ingestion-dev", "analytics-dev"}


def load_config(env: str | None = None) -> dict:
    """
    Load the YAML config for the given environment.

    Args:
        env: Environment name. If None, reads C360_ENV env var. Defaults to 'local'.

    Returns:
        Parsed config as a dict.

    Raises:
        ValueError: If the environment name is not recognised.
        FileNotFoundError: If the config file does not exist.
    """
    if env is None:
        env = os.environ.get("C360_ENV", "local")

    if env not in _VALID_ENVS:
        raise ValueError(
            f"Unknown environment: '{env}'. "
            f"Valid options: {sorted(_VALID_ENVS)}"
        )

    config_path = _REPO_ROOT / "configs" / env / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            f"Verify that configs/{env}/config.yaml exists."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Expand environment variable references in string values
    config = _expand_env_vars(config)

    return config


def _expand_env_vars(obj):
    """Recursively expand ${VAR_NAME} references in config string values."""
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    if isinstance(obj, str) and "${" in obj:
        return os.path.expandvars(obj)
    return obj
