# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for constants module."""

from cli_wizard.constants import __version__


def test_version_exists():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
