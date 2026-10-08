# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for common command utilities."""

import json
import logging

from cli_wizard.commands.common import configure_logging, debug_option, emit_json


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

    def test_configure_logging_keeps_existing_handlers(self):
        """Test a handler already attached, such as a test's, survives."""
        handler = logging.StreamHandler()
        logging.root.addHandler(handler)
        try:
            configure_logging(debug=False)
            assert handler in logging.root.handlers
        finally:
            logging.root.removeHandler(handler)

    def test_configure_logging_applies_the_level_on_a_later_call(self):
        """Test a second invocation in one process still gets its level."""
        configure_logging(debug=False)
        configure_logging(debug=True)
        assert logging.root.level == logging.DEBUG


class TestEmitJson:
    """Tests for emit_json."""

    def test_emit_json_prints_an_indented_document_to_stdout(self, capsys):
        """Test the payload lands on stdout as two-space indented JSON."""
        emit_json({"key": "value", "items": [1]})

        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out == '{\n  "key": "value",\n  "items": [\n    1\n  ]\n}\n'
        assert json.loads(captured.out) == {"key": "value", "items": [1]}


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
