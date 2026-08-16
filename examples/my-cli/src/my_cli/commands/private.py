# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Private commands."""

import json
import os
from pathlib import Path
from typing import Any

import click
from click.core import ParameterSource

from my_cli.client import ApiClient
from my_cli.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_CA_FILE,
)
from my_cli.logging import (
    log_debug,
    log_error,
    set_debug,
)
from my_cli.profile import get_profile_value, load_profile
from my_cli.redaction import redact, redact_text


def _resolve_global(ctx: click.Context, name: str, value: Any) -> Any:
    """Fall back to the root group's value when this level was given none."""
    if ctx.get_parameter_source(name) is ParameterSource.DEFAULT:
        return (ctx.obj or {}).get(name, value)
    return value


def _get_client(
    base_url: str | None,
    no_verify_ssl: bool,
    ca_file: Path | None,
    debug: bool = False,
) -> ApiClient:
    """Create an API client with the given options."""
    effective_base_url = base_url or os.environ.get("API_BASE_URL") or DEFAULT_BASE_URL
    effective_ca_file = (
        None if no_verify_ssl else (str(ca_file) if ca_file else DEFAULT_CA_FILE)
    )
    access_token = get_profile_value("accessToken")
    return ApiClient(
        base_url=effective_base_url,
        access_token=access_token,
        ca_file=effective_ca_file,
        verify_ssl=not no_verify_ssl,
        debug=debug,
    )


@click.group(
    name="private",
    help="Private commands",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output.",
)
@click.pass_context
def private(ctx: click.Context, debug: bool) -> None:
    """Private command group."""
    ctx.ensure_object(dict)
    debug = _resolve_global(ctx, "debug", debug)
    set_debug(debug)
    ctx.obj["debug"] = debug


@private.command(
    name="get-greetings",
    help="Get a greeting message (authenticated)",
)
@click.option(
    "--profile",
    "-p",
    default="default",
    help="Profile name to use.",
)
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output.",
)
@click.option(
    "--base-url",
    "-u",
    envvar="API_BASE_URL",
    help="API base URL.",
)
@click.option(
    "--no-verify-ssl",
    is_flag=True,
    default=False,
    help="Disable SSL certificate verification.",
)
@click.option(
    "--ca-file",
    type=click.Path(
        exists=True,
        dir_okay=False,
        path_type=Path,
    ),
    help="CA certificate file for SSL verification.",
)
@click.pass_context
def get_greetings(
    ctx: click.Context,
    profile: str,
    debug: bool,
    base_url: str | None,
    no_verify_ssl: bool,
    ca_file: Path | None,
) -> None:
    """get_greetings command."""
    # Options given at the root group apply unless repeated here
    profile = _resolve_global(ctx, "profile", profile)
    debug = _resolve_global(ctx, "debug", debug)
    base_url = _resolve_global(ctx, "base_url", base_url)
    no_verify_ssl = _resolve_global(ctx, "no_verify_ssl", no_verify_ssl)
    ca_file = _resolve_global(ctx, "ca_file", ca_file)

    # Enable debug logging if --debug flag is set
    set_debug(debug)

    # Load profile
    load_profile(profile)
    # Log command execution start
    cmd_params: dict[str, Any] = {}
    cmd_name = "private get-greetings"
    log_debug(f"Executing command '{cmd_name}' with params: {redact(cmd_params)}")

    client = _get_client(base_url, no_verify_ssl, ca_file, debug)

    try:
        response = client.get("/private/greetings")
        response.raise_for_status()
        if response.text:
            output = json.dumps(response.json(), indent=2)
            log_debug(
                f"Command '{cmd_name}' completed"
                f" with output: {redact_text(output)[:500]}"
            )
            click.echo(output)
        else:
            log_debug("Command '%s' completed successfully" % cmd_name)
            click.echo("Success")
    except Exception as e:
        log_error(f"Command '{cmd_name}' failed: {e}")
        click.secho(f"Error: {e}", fg="red", err=True)
        raise SystemExit(1)
