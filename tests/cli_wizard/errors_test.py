# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for the errors cli-wizard reports."""

import json
import re
from pathlib import Path

import click
import pytest

import cli_wizard
from cli_wizard.errors import (
    EXIT_ABORTED,
    EXIT_CONFIG,
    EXIT_FAILURE,
    EXIT_FORMATTING,
    EXIT_OUTPUT_DIR,
    EXIT_RUFF_NOT_FOUND,
    EXIT_SPEC,
    EXIT_UNEXPECTED,
    EXIT_USAGE,
    Aborted,
    CliWizardError,
    ConfigError,
    FormattingError,
    OutputDirError,
    RuffNotFoundError,
    SpecError,
    UnexpectedError,
    UsageError,
    reported,
)

SUBCLASSES = [
    ConfigError,
    SpecError,
    OutputDirError,
    RuffNotFoundError,
    FormattingError,
    Aborted,
    UsageError,
    UnexpectedError,
]

SOURCE_ROOT = Path(cli_wizard.__file__).parent

# Ways of failing that bypass the project's own error classes: raising a Click
# class, exiting directly, or letting Click raise on a parameter or a prompt.
FORBIDDEN = re.compile(
    r"raise click\.|raise SystemExit|sys\.exit\(|ctx\.exit\(|ctx\.fail\("
    r"|self\.fail\(|abort=True"
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

    @pytest.mark.parametrize(
        ("cls", "code"),
        [
            (CliWizardError, EXIT_FAILURE),
            (UsageError, EXIT_USAGE),
            (ConfigError, EXIT_CONFIG),
            (SpecError, EXIT_SPEC),
            (OutputDirError, EXIT_OUTPUT_DIR),
            (RuffNotFoundError, EXIT_RUFF_NOT_FOUND),
            (FormattingError, EXIT_FORMATTING),
            (Aborted, EXIT_ABORTED),
            (UnexpectedError, EXIT_UNEXPECTED),
        ],
    )
    def test_every_error_exits_with_its_own_code(self, cls, code):
        """Test each error class carries the code Click exits with."""
        assert cls("boom").exit_code == code

    def test_the_exit_codes_are_distinct_and_leave_zero_alone(self):
        """Test no two classes share a code, none is success, 2 is Click's."""
        codes = [cls("boom").exit_code for cls in (CliWizardError, *SUBCLASSES)]

        assert len(set(codes)) == len(codes)
        assert min(codes) >= 1
        assert EXIT_USAGE == click.UsageError.exit_code

    def test_a_usage_error_is_clicks_too(self):
        """Test a bad invocation is a usage error to Click as well."""
        assert issubclass(UsageError, click.UsageError)

    def test_show_prints_a_json_document_to_stdout(self, capsys):
        """Test showing the error prints it as the JSON a caller can parse."""
        ConfigError("boom").show()

        captured = capsys.readouterr()
        assert captured.err == ""
        assert json.loads(captured.out) == {
            "error": {"type": "ConfigError", "message": "boom", "exitCode": EXIT_CONFIG}
        }

    def test_aborted_needs_no_message(self):
        """Test a declined confirmation reports itself."""
        assert Aborted().format_message() == "Aborted."

    def test_unexpected_error_names_what_it_wraps(self):
        """Test an error that is not the project's own is reported with its type."""
        error = UnexpectedError(RuntimeError("a bug"))

        assert error.format_message() == "RuntimeError: a bug"
        assert error.exit_code == EXIT_UNEXPECTED


class TestReported:
    """Tests for the guard turning what Click raises into the project's errors."""

    def test_the_projects_errors_pass_through(self):
        """Test an error that is already the project's own is left alone."""
        error = ConfigError("boom")
        with pytest.raises(ConfigError) as raised:
            with reported():
                raise error
        assert raised.value is error

    @pytest.mark.parametrize("cls", [click.exceptions.Exit, click.Abort])
    def test_clicks_flow_control_passes_through(self, cls):
        """Test --help's exit and a prompt's abort are Click's to handle."""
        with pytest.raises(cls):
            with reported():
                raise cls()

    def test_a_click_usage_error_becomes_the_projects(self):
        """Test a bad option Click rejected is reported as a usage error."""
        with pytest.raises(UsageError) as raised:
            with reported():
                raise click.BadParameter("bad", param_hint="--api")
        assert raised.value.format_message() == "Invalid value for --api: bad"
        assert isinstance(raised.value.__cause__, click.BadParameter)

    def test_another_click_error_becomes_the_base_error(self):
        """Test a Click error that is not about usage is reported as a failure."""
        with pytest.raises(CliWizardError) as raised:
            with reported():
                raise click.FileError("x.yaml", "unreadable")
        assert type(raised.value) is CliWizardError
        assert "x.yaml" in raised.value.format_message()

    def test_an_unexpected_error_is_wrapped(self):
        """Test a bug is reported as an unexpected error, chained to its cause."""
        with pytest.raises(UnexpectedError) as raised:
            with reported():
                raise RuntimeError("a bug")
        assert isinstance(raised.value.__cause__, RuntimeError)


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
