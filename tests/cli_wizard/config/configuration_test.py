# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration utilities."""

from unittest.mock import patch, mock_open
from cli_wizard.config.configuration import load_default_config


def test_load_default_config():
    """Test loading default configuration."""
    mock_yaml_content = "OpenApiFileName: openapi.json\n"
    with patch("importlib.resources.open_text", mock_open(read_data=mock_yaml_content)):
        config = load_default_config()
        assert config == {"OpenApiFileName": "openapi.json"}


def test_load_default_config_error():
    """Test loading default config with error."""
    with patch("importlib.resources.open_text", side_effect=FileNotFoundError):
        config = load_default_config()
        assert config == {}


def test_load_default_config_invalid_yaml():
    """Test loading default config with invalid YAML."""
    mock_yaml_content = "invalid: yaml: content:"
    with patch("importlib.resources.open_text", mock_open(read_data=mock_yaml_content)):
        config = load_default_config()
        assert config == {}


def test_load_default_config_non_dict():
    """Test loading default config that's not a dict."""
    mock_yaml_content = "- item1\n- item2\n"
    with patch("importlib.resources.open_text", mock_open(read_data=mock_yaml_content)):
        config = load_default_config()
        assert config == {}
