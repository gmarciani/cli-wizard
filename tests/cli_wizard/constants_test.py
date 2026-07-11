# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for constants module."""

import importlib
import importlib.metadata

import cli_wizard.constants as constants_module
from cli_wizard.constants import __version__


def test_version_exists():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_version_fallback_when_package_not_found(monkeypatch):
    """Test that __version__ falls back to '0.0.0' when metadata is unavailable."""

    def fake_version(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    try:
        importlib.reload(constants_module)
        assert constants_module.__version__ == "0.0.0"
    finally:
        monkeypatch.undo()
        importlib.reload(constants_module)
