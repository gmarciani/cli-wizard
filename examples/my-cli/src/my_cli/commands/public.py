# AUTO-GENERATED FILE - DO NOT EDIT
# Generated from OpenAPI specification by cli-wizard

"""Public commands."""

from typing import Any

import click

from my_cli.options import common_options
from my_cli.runner import run_command


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
    cmd_params: dict[str, Any] = {}

    run_command(
        ctx,
        "public get-public-greetings",
        cmd_params,
        lambda client: client.get("/public/greetings"),
    )
