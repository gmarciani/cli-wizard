# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import yaml

from cli_wizard.config.configuration import (
    get_config_path,
    load_default_config,
    load_config,
    save_config,
)


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


def test_get_config_path():
    """Test getting config path."""
    config_path = get_config_path()
    assert config_path.name == "config.yaml"
    assert ".cli_wizard" in str(config_path)


def test_load_config_no_user_config():
    """Test loading config when no user config exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "cli_wizard.config.configuration.load_default_config",
                return_value={"default": "value"},
            ):
                config = load_config()
                assert config == {"default": "value"}


def test_load_config_with_user_config():
    """Test loading config with user config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text("user_key: user_value")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "cli_wizard.config.configuration.load_default_config",
                return_value={"default": "value"},
            ):
                config = load_config()
                assert config["default"] == "value"
                assert config["user_key"] == "user_value"


def test_load_config_user_overrides_default():
    """Test that user config overrides default config."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text("key: user_value")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "cli_wizard.config.configuration.load_default_config",
                return_value={"key": "default_value"},
            ):
                config = load_config()
                assert config["key"] == "user_value"


def test_load_config_invalid_user_yaml():
    """Test loading config with invalid user YAML."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text("invalid: yaml: content:")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "cli_wizard.config.configuration.load_default_config",
                return_value={"default": "value"},
            ):
                config = load_config()
                # Should return default config on error
                assert config == {"default": "value"}


def test_load_config_non_dict_user_config():
    """Test loading config when user config is not a dict."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text("- item1\n- item2")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "cli_wizard.config.configuration.load_default_config",
                return_value={"default": "value"},
            ):
                config = load_config()
                # Should return default config when user config is not a dict
                assert config == {"default": "value"}


def test_save_config():
    """Test saving configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            save_config({"key": "value", "number": 42})

            # Verify file was created and contains correct content
            assert config_path.exists()
            with open(config_path) as f:
                saved = yaml.safe_load(f)
            assert saved["key"] == "value"
            assert saved["number"] == 42
