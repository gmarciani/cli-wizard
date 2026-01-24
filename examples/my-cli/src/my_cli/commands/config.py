# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Config commands for managing CLI profiles."""

import json
from pathlib import Path

import click
import yaml

from my_cli.constants import PROFILE_FILE
from my_cli.logging import log_info, log_error, log_warning


@click.group(name="config", help="Configure the CLI.")
def config() -> None:
    """Config command group."""


@config.command(name="init", help="Initialize the profile file with default profile.")
def config_init() -> None:
    """Init command implementation."""
    if PROFILE_FILE.exists():
        result = {"status": "exists", "path": str(PROFILE_FILE)}
        click.echo(json.dumps(result, indent=2))
        return

    try:
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_content = {"default": {}}
        with open(PROFILE_FILE, "w") as f:
            yaml.safe_dump(default_content, f, default_flow_style=False)
        log_info(f"Created profile file: {PROFILE_FILE}")
        result = {"status": "created", "path": str(PROFILE_FILE)}
        click.echo(json.dumps(result, indent=2))
    except (IOError, OSError) as e:
        log_error(f"Failed to create profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)


@config.command(name="list-profiles", help="List all available profiles.")
def config_list_profiles() -> None:
    """List profiles command implementation."""
    if not PROFILE_FILE.exists():
        result = {"profiles": []}
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)

    result = {"profiles": list(profiles.keys())}
    click.echo(json.dumps(result, indent=2))


@config.command(name="show", help="Show all parameters and values for a profile.")
@click.option("--profile", "-p", default="default", help="Profile name")
def config_show(profile: str) -> None:
    """Show command implementation."""
    if not PROFILE_FILE.exists():
        click.echo(json.dumps({}, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)

    if profile not in profiles:
        click.echo(json.dumps({}, indent=2))
        return

    profile_data = profiles[profile] or {}
    click.echo(json.dumps(profile_data, indent=2))


@config.command(name="get", help="Get a configuration value from a profile.")
@click.argument("param")
@click.option("--profile", "-p", default="default", help="Profile name")
def config_get(param: str, profile: str) -> None:
    """Get command implementation."""
    if not PROFILE_FILE.exists():
        result = {"key": param, "value": None}
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)

    if profile not in profiles:
        result = {"key": param, "value": None}
        click.echo(json.dumps(result, indent=2))
        return

    profile_data = profiles[profile] or {}
    value = profile_data.get(param)
    result = {"key": param, "value": value}
    click.echo(json.dumps(result, indent=2))


@config.command(name="set", help="Set a configuration value in a profile.")
@click.argument("param")
@click.argument("value")
@click.option("--profile", "-p", default="default", help="Profile name")
def config_set(param: str, value: str, profile: str) -> None:
    """Set command implementation."""
    if not PROFILE_FILE.exists():
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        profiles = {}
    else:
        try:
            with open(PROFILE_FILE) as f:
                profiles = yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            log_error(f"Failed to load profile file: {e}")
            result = {"status": "error", "message": str(e)}
            click.echo(json.dumps(result, indent=2), err=True)
            raise SystemExit(1)

    if profile not in profiles:
        profiles[profile] = {}

    # Get old value
    old_value = profiles[profile].get(param)

    # Try to parse value as JSON for complex types
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    profiles[profile][param] = parsed_value

    try:
        with open(PROFILE_FILE, "w") as f:
            yaml.safe_dump(profiles, f, default_flow_style=False)
        log_info(f"Set '{param}' = '{parsed_value}' in profile '{profile}'")
        result = {"key": param, "value": parsed_value, "oldValue": old_value}
        click.echo(json.dumps(result, indent=2))
    except (IOError, OSError) as e:
        log_error(f"Failed to save profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)


@config.command(name="unset", help="Remove a configuration value from a profile.")
@click.argument("param")
@click.option("--profile", "-p", default="default", help="Profile name")
def config_unset(param: str, profile: str) -> None:
    """Unset command implementation."""
    if not PROFILE_FILE.exists():
        result = {"key": param, "oldValue": None}
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(json.dumps(result, indent=2), err=True)
        raise SystemExit(1)

    if profile not in profiles:
        result = {"key": param, "oldValue": None}
        click.echo(json.dumps(result, indent=2))
        return

    profile_data = profiles[profile] or {}
    old_value = profile_data.get(param)

    if param in profile_data:
        del profiles[profile][param]
        try:
            with open(PROFILE_FILE, "w") as f:
                yaml.safe_dump(profiles, f, default_flow_style=False)
            log_info(f"Removed '{param}' from profile '{profile}'")
        except (IOError, OSError) as e:
            log_error(f"Failed to save profile file: {e}")
            result = {"status": "error", "message": str(e)}
            click.echo(json.dumps(result, indent=2), err=True)
            raise SystemExit(1)

    result = {"key": param, "oldValue": old_value}
    click.echo(json.dumps(result, indent=2))
