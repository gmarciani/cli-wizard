# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""The errors cli-wizard reports, one class per kind of failure.

Every failure a command reports is one of these, so a caller can catch them by
class and nothing raises a Click class or exits on its own. They are Click
exceptions, so Click shows them and exits with their code.
"""

from typing import IO, Any

import click


class CliWizardError(click.ClickException):
    """Base of every error cli-wizard reports: shown in red on stderr, exit 1."""

    def show(self, file: IO[Any] | None = None) -> None:
        """Print the error the way the commands report every failure."""
        click.secho(f"✗ {self.format_message()}", fg="red", file=file, err=True)


class ConfigError(CliWizardError):
    """A configuration that cannot be used.

    A generation configuration file that cannot be read, fails validation or
    references itself, or a key or value the tool's own settings reject.
    """


class SpecError(CliWizardError):
    """An OpenAPI spec that cannot be read or parsed."""


class OutputDirError(CliWizardError):
    """An output directory that cannot be cleaned: it holds the configuration
    file, or the command runs from inside it."""


class RuffNotFoundError(CliWizardError):
    """The ruff formatter cannot be run."""


class FormattingError(CliWizardError):
    """Ruff could not format the generated code, so the output cannot be trusted."""


class Aborted(CliWizardError):
    """The user declined a confirmation."""

    def __init__(self, message: str = "Aborted.") -> None:
        super().__init__(message)
