# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Private commands."""

from typing import Any

import click
import requests

from my_cli.client import create_client, request_error, response_error
from my_cli.log import log_debug
from my_cli.options import common_options
from my_cli.output import render
from my_cli.profile import load_profile, resolve_setting
from my_cli.redaction import redact, redact_text


@click.group(
    name="private",
    help="Private commands",
)
@common_options
def private() -> None:
    """Private command group."""


@private.command(
    name="get-greetings",
    help="Get a greeting message (authenticated)",
)
@common_options
@click.pass_context
def get_greetings(
    ctx: click.Context,
) -> None:
    """get_greetings command."""
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
    cmd_name = "private get-greetings"
    log_debug(f"Executing command '{cmd_name}' with params: {redact(cmd_params)}")

    client = create_client(options)

    try:
        response = client.get("/private/greetings")
        response.raise_for_status()
    except requests.RequestException as e:
        raise request_error(cmd_name, e) from e
    if not response.text:
        log_debug(f"Command '{cmd_name}' completed successfully")
        click.echo("Success")
        return
    # Past the request: a body that does not decode is a response, not a
    # failed request, and is reported as such with its own exit code.
    try:
        payload = response.json()
    except ValueError as e:
        raise response_error(cmd_name, response, e) from e
    rendered = render(
        payload,
        output_format,
        json_indent=json_indent,
        table_style=table_style,
    )
    log_debug(
        f"Command '{cmd_name}' completed with output: {redact_text(rendered)[:500]}"
    )
    click.echo(rendered)
