# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for the main CLI module."""

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
    assert "PATH" in result.output
