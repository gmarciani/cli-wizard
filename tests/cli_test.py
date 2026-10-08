# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for the main CLI module."""

import json
import logging
from unittest.mock import patch

from click.testing import CliRunner

from cli_wizard.cli import main


def test_main_help():
    """Test main command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "CLI Wizard" in result.output


def test_version():
    """Test version option."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0


def test_generate_command_exists():
    """Test that generate command is available."""
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Generate the CLI" in result.output


def test_generate_command_options():
    """Test generate command has expected options."""
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--api" in result.output or "-a" in result.output
    assert "--configuration" in result.output or "-c" in result.output
    assert "--output" in result.output or "-o" in result.output
    assert "PATH" not in result.output


def _error(result):
    """Parse the error document a failed invocation printed."""
    return json.loads(result.stdout)["error"]


def test_a_bad_option_is_reported_as_json():
    """Test an option Click rejects itself is still reported as JSON, exit 2."""
    result = CliRunner().invoke(main, ["generate", "--api", "/no/such/spec.json"])

    assert result.exit_code == 2
    error = _error(result)
    assert error["type"] == "UsageError"
    assert error["exitCode"] == 2
    assert "/no/such/spec.json" in error["message"]


def test_an_unknown_command_is_reported_as_json():
    """Test a command that does not exist is a usage error in JSON."""
    result = CliRunner().invoke(main, ["frobnicate"])

    assert result.exit_code == 2
    assert _error(result) == {
        "type": "UsageError",
        "message": "No such command 'frobnicate'.",
        "exitCode": 2,
    }


def test_an_unexpected_error_is_reported_as_json(tmp_path):
    """Test a bug is reported as JSON naming its type, with exit code 1."""
    with patch(
        "cli_wizard.commands.generate.resolve_ruff", side_effect=RuntimeError("a bug")
    ):
        result = CliRunner().invoke(
            main, ["generate", "--project-name", "X", "--output", str(tmp_path / "o")]
        )

    assert result.exit_code == 1
    assert _error(result) == {
        "type": "UnexpectedError",
        "message": "RuntimeError: a bug",
        "exitCode": 1,
    }


def test_an_unexpected_errors_traceback_is_logged_under_debug(tmp_path, caplog):
    """Test the traceback a bug came with is kept in the debug log."""
    caplog.set_level(logging.DEBUG, logger="cli_wizard.cli")
    with patch(
        "cli_wizard.commands.generate.resolve_ruff", side_effect=RuntimeError("a bug")
    ):
        result = CliRunner().invoke(
            main,
            ["--debug", "generate", "--project-name", "X", "--output", str(tmp_path)],
        )

    assert result.exit_code == 1
    assert "Traceback (most recent call last)" in caplog.text
    assert "RuntimeError: a bug" in caplog.text


def test_help_stays_text():
    """Test --help is not forced into JSON."""
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert result.output.startswith("Usage:")
