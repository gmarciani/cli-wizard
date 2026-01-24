# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration utilities for CLI Wizard."""

import yaml
from pathlib import Path
from typing import Dict, Any

from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.config.schema import Config


def get_config_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".cli_wizard"
    config_dir.mkdir(exist_ok=True)
    return config_dir / CONFIG_FILE_NAME


def load_config() -> Dict[str, Any]:
    """Load configuration from file, using schema defaults for missing values."""
    config_path = get_config_path()

    if not config_path.exists():
        # Return schema defaults
        return Config().model_dump()

    try:
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
            if isinstance(user_config, dict):
                # Validate and merge with schema defaults
                validated = Config(**user_config)
                return validated.model_dump()
            return Config().model_dump()
    except (yaml.YAMLError, IOError):
        return Config().model_dump()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, indent=2)
