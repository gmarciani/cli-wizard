# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Main CLI module for CLI Wizard."""

import click
import logging
from cli_wizard.constants import __version__
from cli_wizard.commands.config import config
from cli_wizard.commands.generate import generate


@click.group()
@click.version_option(version=__version__, prog_name="cli-wizard")
@click.option("--debug", "-d", is_flag=True, help="Enable debug output")
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """CLI Wizard - Generate modern CLI from OpenAPI."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    # Configure logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    logging.Formatter.converter = lambda *args: __import__("time").gmtime()


main.add_command(config)
main.add_command(generate)


if __name__ == "__main__":
    main()
