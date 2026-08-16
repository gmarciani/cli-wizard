# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Private commands."""

import json
from pathlib import Path
from typing import Any

import click
from click.core import ParameterSource

from my_cli.client import ApiClient, format_error
from my_cli.constants import DEFAULT_CA_FILE
from my_cli.logging import (
    colors_enabled,
    log_debug,
    log_error,
    set_debug,
)
from my_cli.profile import load_profile, resolve_setting
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
    """Create an API client with the given options.

    baseUrl, timeout and accessToken are profile settings, so resolve_setting()
    runs the precedence chain over them; --base-url is the only one with a flag
    to outrank it. --no-verify-ssl and --ca-file have no key in
    PROFILE_DEFAULTS and so come from the command line alone.
    """
    effective_ca_file = (
        None if no_verify_ssl else (str(ca_file) if ca_file else DEFAULT_CA_FILE)
    )
    return ApiClient(
        base_url=resolve_setting("baseUrl", base_url),
        access_token=resolve_setting("accessToken"),
        timeout=int(resolve_setting("timeout")),
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
            indent = int(resolve_setting("jsonIndent"))
            output = json.dumps(response.json(), indent=indent)
            log_debug(
                f"Command '{cmd_name}' completed"
                f" with output: {redact_text(output)[:500]}"
            )
            click.echo(output)
        else:
            log_debug("Command '%s' completed successfully" % cmd_name)
            click.echo("Success")
    except Exception as e:
        message = format_error(e)
        log_error(f"Command '{cmd_name}' failed: {message}")
        click.secho(
            f"Error: {message}",
            fg="red" if colors_enabled() else None,
            err=True,
        )
        raise SystemExit(1)
