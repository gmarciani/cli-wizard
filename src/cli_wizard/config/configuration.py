# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration utilities for CLI Wizard."""

import yaml
from pathlib import Path
from typing import Dict, Any
import importlib.resources


def get_config_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".cli_wizard"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.yaml"


def load_default_config() -> Dict[str, Any]:
    """Load default configuration from packaged default_config.yaml."""
    try:
        with importlib.resources.open_text(
            "cli_wizard.config", "default_config.yaml"
        ) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except (yaml.YAMLError, IOError, FileNotFoundError):
        return {}


def load_config() -> Dict[str, Any]:
    """Load configuration from file, merging with defaults."""
    default_config = load_default_config()
    config_path = get_config_path()

    if not config_path.exists():
        return default_config

    try:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
            if isinstance(user_config, dict):
                default_config.update(user_config)
            return default_config
    except (yaml.YAMLError, IOError):
        return default_config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, indent=2)
