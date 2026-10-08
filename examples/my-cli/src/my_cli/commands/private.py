# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Private commands."""

from typing import Any

import click

from my_cli.options import common_options
from my_cli.runner import run_command


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
    cmd_params: dict[str, Any] = {}

    run_command(
        ctx,
        "private get-greetings",
        cmd_params,
        lambda client: client.get("/private/greetings"),
    )
