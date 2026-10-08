# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Main CLI module for CLI Wizard."""

import logging
import traceback
from typing import Any

import click

from cli_wizard.commands.bootstrap import bootstrap
from cli_wizard.commands.common import configure_logging, debug_option
from cli_wizard.commands.config import config
from cli_wizard.commands.generate import generate
from cli_wizard.constants import __version__
from cli_wizard.errors import UnexpectedError, reported

logger = logging.getLogger(__name__)


class RootGroup(click.Group):
    """The root group, reporting what Click raises on its own as JSON too.

    Click's main() shows a ClickException and exits with its code; wrapping the
    parsing and the dispatch turns everything else into one of cli-wizard's
    errors first, so every failure is the one JSON document on stdout.
    """

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        with reported():
            return super().make_context(info_name, args, parent, **extra)

    def invoke(self, ctx: click.Context) -> Any:
        try:
            with reported():
                return super().invoke(ctx)
        except UnexpectedError as e:
            # The traceback the bug came with, kept for --debug
            logger.debug("".join(traceback.format_exception(e.__cause__)))
            raise


@click.group(cls=RootGroup, help="CLI Wizard - Generate modern CLI from OpenAPI.")
@click.version_option(version=__version__, prog_name="cli-wizard")
@debug_option
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """Main CLI entry point."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    configure_logging(debug)


main.add_command(bootstrap)
main.add_command(config)
main.add_command(generate)


if __name__ == "__main__":
    main()
