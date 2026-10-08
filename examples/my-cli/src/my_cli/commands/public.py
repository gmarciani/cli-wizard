# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Public commands."""

from typing import Any

import click

from my_cli.client import create_client, format_error
from my_cli.log import colors_enabled, log_debug, log_error
from my_cli.options import common_options
from my_cli.output import render
from my_cli.profile import load_profile, resolve_setting
from my_cli.redaction import redact, redact_text


@click.group(
    name="public",
    help="Public commands",
)
@common_options
def public() -> None:
    """Public command group."""


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

    # Load the profile
    load_profile(ctx)

    # Resolved before the request, so a bad setting fails without sending it
    output_format = str(resolve_setting("outputFormat", options["output"]))
    json_indent = int(resolve_setting("jsonIndent"))
    table_style = str(resolve_setting("tableStyle"))
    # Log command execution start
    cmd_params: dict[str, Any] = {}
    cmd_name = "public get-public-greetings"
    log_debug(f"Executing command '{cmd_name}' with params: {redact(cmd_params)}")

    client = create_client(options)

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
