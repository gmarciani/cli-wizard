# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""The errors cli-wizard reports, one class per kind of failure.

Every failure a command reports is one of these, so a caller can catch them by
class and nothing raises a Click class or exits on its own. They are Click
exceptions, so Click shows them and exits with their code. Shown, an error is
one JSON document on stdout, the only thing a failed invocation prints there::

    {"error": {"type": "ConfigError", "message": "...", "exitCode": 1}}
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import IO, Any

import click

# Exit codes, one per error class, so a calling script can tell the failures
# apart. 2 is Click's own, for a usage error, and 1 is what is left: a Click
# error that is not about usage.
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_SPEC = 4
EXIT_OUTPUT_DIR = 5
EXIT_RUFF_NOT_FOUND = 6
EXIT_FORMATTING = 7
EXIT_ABORTED = 8
EXIT_UNEXPECTED = 9


class CliWizardError(click.ClickException):
    """Base of every error cli-wizard reports: a JSON document on stdout, and
    the exit code of its class."""

    exit_code = EXIT_FAILURE

    def to_dict(self) -> dict[str, Any]:
        """The document a caller parses: the class, the message and the code."""
        return {
            "error": {
                "type": type(self).__name__,
                "message": self.format_message(),
                "exitCode": self.exit_code,
            }
        }

    def show(self, file: IO[Any] | None = None) -> None:
        """Print the error document to stdout, where the result would have gone."""
        click.echo(json.dumps(self.to_dict(), indent=2), file=file)


class ConfigError(CliWizardError):
    """A configuration that cannot be used.

    A generation configuration file that cannot be read, fails validation or
    references itself, or a key or value the tool's own settings reject.
    """

    exit_code = EXIT_CONFIG


class SpecError(CliWizardError):
    """An OpenAPI spec that cannot be read or parsed."""

    exit_code = EXIT_SPEC


class OutputDirError(CliWizardError):
    """An output directory that cannot be cleaned: it holds the configuration
    file, or the command runs from inside it."""

    exit_code = EXIT_OUTPUT_DIR


class RuffNotFoundError(CliWizardError):
    """The ruff formatter cannot be run."""

    exit_code = EXIT_RUFF_NOT_FOUND


class FormattingError(CliWizardError):
    """Ruff could not format the generated code, so the output cannot be trusted."""

    exit_code = EXIT_FORMATTING


class Aborted(CliWizardError):
    """The user declined a confirmation."""

    exit_code = EXIT_ABORTED

    def __init__(self, message: str = "Aborted.") -> None:
        super().__init__(message)


class UsageError(CliWizardError, click.UsageError):
    """A bad invocation: an unknown command, a missing option or a bad value.

    What Click raises itself while parsing, wrapped by ``reported`` so it is
    shown as JSON like every other failure, with Click's exit code for it.
    """

    exit_code = EXIT_USAGE


class UnexpectedError(CliWizardError):
    """An error that is not cli-wizard's own: a bug, reported with its type."""

    exit_code = EXIT_UNEXPECTED

    def __init__(self, error: BaseException) -> None:
        super().__init__(f"{type(error).__name__}: {error}")


@contextmanager
def reported() -> Iterator[None]:
    """Turn whatever escapes the block into one of cli-wizard's errors.

    Click's main() shows a ClickException and exits with its code, so wrapping
    the parsing and the dispatch of the root group in this guard makes every
    failure a JSON document on stdout. cli-wizard's own errors and Click's flow
    control, the exit behind --help and the abort behind a prompt, pass through.
    """
    try:
        yield
    except (CliWizardError, click.exceptions.Exit, click.Abort, EOFError):
        raise
    except click.UsageError as e:
        raise UsageError(e.format_message()) from e
    except click.ClickException as e:
        raise CliWizardError(e.format_message()) from e
    except Exception as e:
        raise UnexpectedError(e) from e
