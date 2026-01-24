# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Constants for CLI Wizard."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("cli-wizard")
except PackageNotFoundError:
    __version__ = "0.0.0"

CONFIG_FILE_NAME = "cli-wizard.yaml"
