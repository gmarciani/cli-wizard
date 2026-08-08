# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration utilities for CLI Wizard.

``load_stored_config`` returns only the keys the user explicitly set, and that
is what gets persisted. ``load_config`` returns those merged over the schema
defaults with derivations applied, and that is what consumers read. Keeping
them apart is what lets a later ``ProjectName`` change re-derive
``CommandName`` instead of being pinned by a value that was only ever a
default.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME

logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """Get the configuration file path."""
    config_dir = Path.home() / ".cli_wizard"
    config_dir.mkdir(exist_ok=True)
    return config_dir / CONFIG_FILE_NAME


def load_stored_config() -> Dict[str, Any]:
    """Load only the values explicitly stored in the config file.

    A file that cannot be read, parsed or validated degrades to an empty
    config with a warning, so it can never lock the user out of the commands
    that would repair it.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            stored = yaml.safe_load(f)
        if not isinstance(stored, dict):
            raise ValueError("file does not contain a mapping")
        Config(**stored)  # Validate only; load_config() builds the merged view.
        return stored
    except (yaml.YAMLError, IOError, ValueError) as e:
        # Pydantic's ValidationError is a ValueError.
        logger.warning(
            f"Ignoring invalid configuration file '{config_path}' ({e}). "
            "Run 'cli-wizard config reset' to recreate it."
        )
        return {}


def load_config() -> Dict[str, Any]:
    """Load configuration from file, using schema defaults for missing values."""
    return Config(**load_stored_config()).model_dump()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file, validating and coercing it first.

    Only the keys present in ``config`` are persisted: writing back the full
    merged dump would freeze derived values such as ``CommandName``.
    """
    validated = Config(**config)
    stored = {key: getattr(validated, key) for key in config}

    config_path = get_config_path()
    with open(config_path, "w") as f:
        yaml.safe_dump(stored, f, indent=2)
