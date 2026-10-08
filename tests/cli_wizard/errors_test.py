# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for the errors cli-wizard reports."""

import re
from pathlib import Path

import click
import pytest

import cli_wizard
from cli_wizard.errors import (
    Aborted,
    CliWizardError,
    ConfigError,
    FormattingError,
    OutputDirError,
    RuffNotFoundError,
    SpecError,
)

SUBCLASSES = [
    ConfigError,
    SpecError,
    OutputDirError,
    RuffNotFoundError,
    FormattingError,
    Aborted,
]

SOURCE_ROOT = Path(cli_wizard.__file__).parent

# Ways of failing that bypass the project's own error classes: raising a Click
# class, exiting directly, or letting Click raise on a parameter or a prompt.
FORBIDDEN = re.compile(
    r"raise click\.|raise SystemExit|sys\.exit\(|ctx\.exit\(|ctx\.fail\("
    r"|self\.fail\(|abort=True|click\.Abort"
)


class TestCliWizardError:
    """Tests for the base error and what it has in common with its subclasses."""

    def test_is_reported_by_click(self):
        """Test the base error is one Click shows and exits on by itself."""
        assert issubclass(CliWizardError, click.ClickException)

    @pytest.mark.parametrize("cls", SUBCLASSES)
    def test_every_error_is_a_cli_wizard_error(self, cls):
        """Test each failure class derives from the one base."""
        assert issubclass(cls, CliWizardError)

    @pytest.mark.parametrize("cls", [CliWizardError, *SUBCLASSES])
    def test_every_error_exits_with_one(self, cls):
        """Test every failure exits with the generic failure code."""
        assert cls("boom").exit_code == 1

    def test_show_prints_the_message_marked_to_stderr(self, capsys):
        """Test showing the error prints it the way the commands report failures."""
        CliWizardError("boom").show()

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "✗ boom\n"

    def test_aborted_needs_no_message(self):
        """Test a declined confirmation reports itself."""
        assert Aborted().format_message() == "Aborted."


class TestOnlyProjectErrorsAreRaised:
    """cli-wizard and the generated code report failures through their own classes."""

    @pytest.mark.parametrize(
        "path",
        sorted(
            [
                *(SOURCE_ROOT.glob("*.py")),
                *(SOURCE_ROOT / "commands").glob("*.py"),
                *(SOURCE_ROOT / "config").glob("*.py"),
                *(SOURCE_ROOT / "generator").glob("*.py"),
                *(SOURCE_ROOT / "templates" / "src").rglob("*.j2"),
            ]
        ),
        ids=lambda path: str(path.relative_to(SOURCE_ROOT)),
    )
    def test_no_click_exception_or_direct_exit(self, path):
        """Test a source file never raises a Click class or exits on its own."""
        offending = [
            f"{number}: {line.strip()}"
            for number, line in enumerate(path.read_text().splitlines(), 1)
            if FORBIDDEN.search(line)
        ]
        assert not offending, "\n".join(offending)
