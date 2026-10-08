# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""What every cli-wizard command shares: logging, the --debug option, output."""

import json
import logging
import time
from typing import Any

import click

logger = logging.getLogger(__name__)


def configure_logging(debug: bool = False) -> None:
    """Configure logging with UTC timestamps, at DEBUG level under --debug.

    Args:
        debug: Whether to enable debug level logging
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    # basicConfig is a no-op once the root logger has handlers, so a later
    # invocation in the same process still gets the level it asked for
    logging.root.setLevel(level)
    logging.Formatter.converter = time.gmtime


debug_option = click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output",
)


def emit_json(payload: Any) -> None:
    """Print a command's result, the one JSON document stdout carries."""
    click.echo(json.dumps(payload, indent=2))
