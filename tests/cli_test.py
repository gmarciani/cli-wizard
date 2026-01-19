# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for the main CLI module."""

import logging
from click.testing import CliRunner
from unittest.mock import patch
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
    assert "1.0.0" in result.output


def test_debug_flag():
    """Test debug flag."""
    runner = CliRunner()
    with patch("cli_wizard.cli.logging.basicConfig") as mock_logging:
        with patch("cli_wizard.commands.config.load_config") as mock_load:
            mock_load.return_value = {"apikey": None}
            result = runner.invoke(main, ["--debug", "config", "show"])
            assert result.exit_code == 0
            mock_logging.assert_called_once()
            args, kwargs = mock_logging.call_args
            assert kwargs["level"] == logging.DEBUG


def test_no_debug_flag():
    """Test without debug flag."""
    runner = CliRunner()
    with patch("cli_wizard.cli.logging.basicConfig") as mock_logging:
        with patch("cli_wizard.commands.config.load_config") as mock_load:
            mock_load.return_value = {"apikey": None}
            result = runner.invoke(main, ["config", "show"])
            assert result.exit_code == 0
            mock_logging.assert_called_once()
            args, kwargs = mock_logging.call_args
            assert kwargs["level"] == logging.INFO
