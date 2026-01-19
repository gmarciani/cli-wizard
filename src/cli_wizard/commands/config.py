# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration commands for CLI Wizard."""

import click
import logging
import json
from cli_wizard.config.configuration import (
    load_config,
    save_config,
    get_config_path,
)

logger = logging.getLogger(__name__)


@click.group()
def config() -> None:
    """Manage configurations."""


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a configuration value."""
    cfg = load_config()
    old_value = cfg.get(key)
    cfg[key] = value
    save_config(cfg)

    result = {"key": key, "value": value, "oldValue": old_value}
    print(json.dumps(result, indent=2))


@config.command()
@click.argument("key")
def get(key: str) -> None:
    """Get a configuration value."""
    cfg = load_config()
    if key not in cfg:
        logger.error(f"Unknown configuration key '{key}'")
        return

    result = {"key": key, "value": cfg[key]}
    print(json.dumps(result, indent=2))


@config.command()
@click.argument("key")
def unset(key: str) -> None:
    """Unset a configuration value (set to None)."""
    cfg = load_config()
    if key not in cfg:
        logger.error(f"Unknown configuration key '{key}'")
        return

    old_value = cfg.get(key)
    cfg[key] = None
    save_config(cfg)

    result = {"key": key, "value": None, "oldValue": old_value}
    print(json.dumps(result, indent=2))


@config.command()
def show() -> None:
    """Show all configuration values as JSON."""
    cfg = load_config()
    print(json.dumps(cfg, indent=2))


@config.command()
def reset() -> None:
    """Reset configuration to defaults and delete local config file."""
    cfg = load_config()
    print(json.dumps(cfg, indent=2))

    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()
