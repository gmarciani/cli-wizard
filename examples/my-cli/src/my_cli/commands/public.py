# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Public commands."""

from typing import Any

import click

from my_cli.client import ApiClient, format_error
from my_cli.constants import DEFAULT_CA_FILE
from my_cli.logging import (
    colors_enabled,
    log_debug,
    log_error,
    set_debug,
)
from my_cli.options import common_options
from my_cli.output import render
from my_cli.profile import load_profile, resolve_setting
from my_cli.redaction import redact, redact_text


def _get_client(options: dict[str, Any]) -> ApiClient:
    """Create an API client from the common options.

    baseUrl, timeout, accessToken and the retry settings are profile settings,
    so resolve_setting() runs the precedence chain over them; --base-url and
    --timeout are the ones with a flag to outrank it. --no-verify-ssl,
    --ca-file and --header have no key in PROFILE_DEFAULTS and so come from
    the command line alone.
    """
    no_verify_ssl = options["no_verify_ssl"]
    ca_file = options["ca_file"]
    if no_verify_ssl:
        effective_ca_file = None
    else:
        effective_ca_file = str(ca_file) if ca_file else DEFAULT_CA_FILE
    return ApiClient(
        base_url=resolve_setting("baseUrl", options["base_url"]),
        access_token=resolve_setting("accessToken"),
        timeout=int(resolve_setting("timeout", options["timeout"])),
        ca_file=effective_ca_file,
        verify_ssl=not no_verify_ssl,
        debug=options["debug"],
        headers=dict(options["header"]),
        retry_max_attempts=int(resolve_setting("retryMaxAttempts")),
        retry_backoff_factor=float(resolve_setting("retryBackoffFactor")),
    )


@click.group(
    name="public",
    help="Public commands",
)
@common_options
@click.pass_context
def public(ctx: click.Context) -> None:
    """Public command group."""
    set_debug(ctx.obj["debug"])


@public.command(
    name="get-public-greetings",
    help="Get a public greeting message",
)
@common_options
@click.pass_context
def get_public_greetings(
    ctx: click.Context,
) -> None:
    """get_public_greetings command."""
    # The common options, from whichever level they were given at
    options = ctx.obj

    # Enable debug logging if --debug flag is set
    set_debug(options["debug"])

    # Load profile
    load_profile(options["profile"])

    # Resolved before the request, so a bad setting fails without sending it
    output_format = str(resolve_setting("outputFormat", options["output"]))
    json_indent = int(resolve_setting("jsonIndent"))
    table_style = str(resolve_setting("tableStyle"))
    # Log command execution start
    cmd_params: dict[str, Any] = {}
    cmd_name = "public get-public-greetings"
    log_debug(f"Executing command '{cmd_name}' with params: {redact(cmd_params)}")

    client = _get_client(options)

    try:
        response = client.get("/public/greetings")
        response.raise_for_status()
        if response.text:
            rendered = render(
                response.json(),
                output_format,
                json_indent=json_indent,
                table_style=table_style,
            )
            log_debug(
                f"Command '{cmd_name}' completed"
                f" with output: {redact_text(rendered)[:500]}"
            )
            click.echo(rendered)
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
