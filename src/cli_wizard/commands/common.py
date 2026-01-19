# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Common utilities for CLI Wizard commands."""

import click
import logging

logger = logging.getLogger(__name__)


def configure_logging(debug: bool = False) -> None:
    """Configure logging with UTC timestamps.

    Args:
        debug: Whether to enable debug level logging
    """
    import time

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    logging.Formatter.converter = time.gmtime


debug_option = click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Enable debug output",
)
