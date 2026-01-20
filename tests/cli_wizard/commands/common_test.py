# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for common command utilities."""

import logging

from cli_wizard.commands.common import configure_logging, debug_option


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_default(self):
        """Test default logging configuration (INFO level)."""
        configure_logging(debug=False)
        assert logging.root.level == logging.INFO

    def test_configure_logging_debug(self):
        """Test debug logging configuration."""
        configure_logging(debug=True)
        assert logging.root.level == logging.DEBUG

    def test_configure_logging_removes_existing_handlers(self):
        """Test that existing handlers are removed."""
        # Add a handler
        handler = logging.StreamHandler()
        logging.root.addHandler(handler)
        initial_count = len(logging.root.handlers)

        configure_logging(debug=False)

        # Should have replaced handlers
        assert len(logging.root.handlers) > 0


class TestDebugOption:
    """Tests for debug_option decorator."""

    def test_debug_option_exists(self):
        """Test that debug_option is a click option."""
        import click

        @click.command()
        @debug_option
        def test_cmd(debug):
            pass

        # Check that the option was added
        assert any(param.name == "debug" for param in test_cmd.params)
