# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Config commands for managing CLI profiles."""

import json
from typing import Any

import click
import yaml

from my_cli.constants import PROFILE_DEFAULTS, PROFILE_FILE
from my_cli.log import log_error, log_info
from my_cli.options import common_options


@click.group(name="config", help="Configure the CLI.")
@common_options
def config() -> None:
    """Config command group."""


@config.command(
    name="init",
    help="Initialize the profile file with default profile.",
)
@common_options
def config_init() -> None:
    """Init command implementation."""
    if PROFILE_FILE.exists():
        result: dict[str, Any] = {
            "status": "exists",
            "path": str(PROFILE_FILE),
        }
        click.echo(json.dumps(result, indent=2))
        return

    try:
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        PROFILE_FILE.touch(mode=0o600, exist_ok=True)
        default_content: dict[str, dict[str, Any]] = {
            "default": {},
        }
        with open(PROFILE_FILE, "w") as f:
            yaml.safe_dump(
                default_content,
                f,
                default_flow_style=False,
            )
        log_info(f"Created profile file: {PROFILE_FILE}")
        result = {
            "status": "created",
            "path": str(PROFILE_FILE),
        }
        click.echo(json.dumps(result, indent=2))
    except OSError as e:
        log_error(f"Failed to create profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)


@config.command(
    name="list-profiles",
    help="List all available profiles.",
)
@common_options
def config_list_profiles() -> None:
    """List profiles command implementation."""
    if not PROFILE_FILE.exists():
        result: dict[str, Any] = {"profiles": []}
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles: dict[str, Any] = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)

    result = {"profiles": list(profiles.keys())}
    click.echo(json.dumps(result, indent=2))


@config.command(
    name="show",
    help="Show all parameters and values for a profile.",
)
@common_options
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show command implementation."""
    profile = ctx.obj["profile"]
    if not PROFILE_FILE.exists():
        click.echo(json.dumps({}, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles: dict[str, Any] = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        log_error(f"Failed to load profile file: {e}")
        result: dict[str, Any] = {
            "status": "error",
            "message": str(e),
        }
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)

    if profile not in profiles:
        click.echo(json.dumps({}, indent=2))
        return

    profile_data: dict[str, Any] = profiles[profile] or {}
    merged: dict[str, Any] = {
        **PROFILE_DEFAULTS,
        **profile_data,
    }
    click.echo(json.dumps(merged, indent=2))


@config.command(
    name="get",
    help="Get a configuration value from a profile.",
)
@click.option(
    "--param",
    required=True,
    help="Parameter name.",
)
@common_options
@click.pass_context
def config_get(ctx: click.Context, param: str) -> None:
    """Get command implementation."""
    profile = ctx.obj["profile"]
    if not PROFILE_FILE.exists():
        result: dict[str, Any] = {
            "key": param,
            "value": None,
        }
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles: dict[str, Any] = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)

    if profile not in profiles:
        result = {"key": param, "value": None}
        click.echo(json.dumps(result, indent=2))
        return

    profile_data: dict[str, Any] = profiles[profile] or {}
    value = profile_data.get(param)
    result = {"key": param, "value": value}
    click.echo(json.dumps(result, indent=2))


@config.command(
    name="set",
    help="Set a configuration value in a profile.",
)
@click.option(
    "--param",
    required=True,
    help="Parameter name.",
)
@click.option(
    "--value",
    required=True,
    help="Parameter value.",
)
@common_options
@click.pass_context
def config_set(ctx: click.Context, param: str, value: str) -> None:
    """Set command implementation."""
    profile = ctx.obj["profile"]
    profiles: dict[str, Any]
    result: dict[str, Any]
    if not PROFILE_FILE.exists():
        profiles = {}
    else:
        try:
            with open(PROFILE_FILE) as f:
                profiles = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            log_error(f"Failed to load profile file: {e}")
            result = {
                "status": "error",
                "message": str(e),
            }
            click.echo(
                json.dumps(result, indent=2),
                err=True,
            )
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
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        PROFILE_FILE.touch(mode=0o600, exist_ok=True)
        # Tighten files left world-readable by older versions
        PROFILE_FILE.chmod(0o600)
        with open(PROFILE_FILE, "w") as f:
            yaml.safe_dump(
                profiles,
                f,
                default_flow_style=False,
            )
        log_info(f"Set '{param}' = '{parsed_value}' in profile '{profile}'")
        result = {
            "key": param,
            "value": parsed_value,
            "oldValue": old_value,
        }
        click.echo(json.dumps(result, indent=2))
    except OSError as e:
        log_error(f"Failed to save profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)


@config.command(
    name="unset",
    help="Remove a configuration value from a profile.",
)
@click.option(
    "--param",
    required=True,
    help="Parameter name.",
)
@common_options
@click.pass_context
def config_unset(ctx: click.Context, param: str) -> None:
    """Unset command implementation."""
    profile = ctx.obj["profile"]
    if not PROFILE_FILE.exists():
        result: dict[str, Any] = {
            "key": param,
            "oldValue": None,
        }
        click.echo(json.dumps(result, indent=2))
        return

    try:
        with open(PROFILE_FILE) as f:
            profiles: dict[str, Any] = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        log_error(f"Failed to load profile file: {e}")
        result = {"status": "error", "message": str(e)}
        click.echo(
            json.dumps(result, indent=2),
            err=True,
        )
        raise SystemExit(1)

    if profile not in profiles:
        result = {"key": param, "oldValue": None}
        click.echo(json.dumps(result, indent=2))
        return

    profile_data: dict[str, Any] = profiles[profile] or {}
    old_value = profile_data.get(param)

    if param in profile_data:
        del profiles[profile][param]
        try:
            with open(PROFILE_FILE, "w") as f:
                yaml.safe_dump(
                    profiles,
                    f,
                    default_flow_style=False,
                )
            log_info(f"Removed '{param}' from profile '{profile}'")
        except OSError as e:
            log_error(f"Failed to save profile file: {e}")
            result = {
                "status": "error",
                "message": str(e),
            }
            click.echo(
                json.dumps(result, indent=2),
                err=True,
            )
            raise SystemExit(1)

    result = {"key": param, "oldValue": old_value}
    click.echo(json.dumps(result, indent=2))
