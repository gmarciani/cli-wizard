# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration commands for CLI Wizard."""

import json
import logging

import click
from pydantic import ValidationError

from cli_wizard.config.configuration import (
    get_config_path,
    load_config,
    load_stored_config,
    save_config,
)
from cli_wizard.config.schema import Config

logger = logging.getLogger(__name__)


def _check_known_key(key: str) -> None:
    """Abort if the key is not a configuration field."""
    if key not in Config.model_fields:
        raise click.ClickException(f"Unknown configuration key '{key}'")


@click.group(help="Manage configurations.")
def config() -> None:
    """Config command group implementation."""


@config.command(help="Set a configuration value.")
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set command implementation."""
    _check_known_key(key)

    stored = load_stored_config()
    old_value = load_config().get(key)

    try:
        stored[key] = Config.parse_cli_value(key, value)
        save_config(stored)
    except ValidationError as e:
        detail = "; ".join(item["msg"] for item in e.errors())
        raise click.ClickException(f"Invalid value for '{key}': {detail}") from e
    except ValueError as e:
        raise click.ClickException(f"Invalid value for '{key}': {e}") from e

    result = {"key": key, "value": load_config()[key], "oldValue": old_value}
    print(json.dumps(result, indent=2))


@config.command(help="Get a configuration value.")
@click.argument("key")
def get(key: str) -> None:
    """Get command implementation."""
    _check_known_key(key)

    result = {"key": key, "value": load_config()[key]}
    print(json.dumps(result, indent=2))


@config.command(help="Unset a configuration value, reverting it to the default.")
@click.argument("key")
def unset(key: str) -> None:
    """Unset command implementation.

    Removes the key so the schema default applies again. Every field has a
    default, so this cannot leave a config the schema rejects.
    """
    _check_known_key(key)

    stored = load_stored_config()
    if key in stored:
        old_value = stored.pop(key)
        save_config(stored)
    else:
        logger.info(f"'{key}' is not set; it already uses the schema default.")
        old_value = None

    result = {"key": key, "value": load_config()[key], "oldValue": old_value}
    print(json.dumps(result, indent=2))


@config.command(help="Show all configuration values as JSON.")
def show() -> None:
    """Show command implementation."""
    print(json.dumps(load_config(), indent=2))


@config.command(help="Reset configuration to defaults and delete local config file.")
def reset() -> None:
    """Reset command implementation.

    Deletes before reading: this is the way back from a config file the schema
    rejects, so it must not depend on that file being loadable.
    """
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()

    print(json.dumps(Config().model_dump(), indent=2))
