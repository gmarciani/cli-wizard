# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration utilities."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from cli_wizard.config.configuration import (
    get_config_path,
    load_config,
    save_config,
)
from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME


def test_get_config_path():
    """Test getting config path."""
    config_path = get_config_path()
    assert config_path.name == CONFIG_FILE_NAME
    assert ".cli_wizard" in str(config_path)


def test_load_config_no_user_config():
    """Test loading config when no user config exists returns schema defaults."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME
        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            config = load_config()
            # Should return schema defaults
            defaults = Config().model_dump()
            assert config == defaults


def test_load_config_with_user_config():
    """Test loading config with user config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME
        config_path.write_text("CommandName: my-cli\nPackageName: my_cli\n")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            config = load_config()
            assert config["CommandName"] == "my-cli"
            assert config["PackageName"] == "my_cli"
            # Schema defaults should be present for other fields
            assert "ProjectName" in config


def test_load_config_user_overrides_default():
    """Test that user config overrides schema defaults."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME
        config_path.write_text("Version: 2.0.0\n")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            config = load_config()
            assert config["Version"] == "2.0.0"


def test_load_config_invalid_user_yaml():
    """Test loading config with invalid user YAML returns schema defaults."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME
        config_path.write_text("invalid: yaml: content:")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            config = load_config()
            # Should return schema defaults on error
            defaults = Config().model_dump()
            assert config == defaults


def test_load_config_non_dict_user_config():
    """Test loading config when user config is not a dict returns schema defaults."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME
        config_path.write_text("- item1\n- item2")

        with patch(
            "cli_wizard.config.configuration.get_config_path",
            return_value=config_path,
        ):
            config = load_config()
            # Should return schema defaults when user config is not a dict
            defaults = Config().model_dump()
            assert config == defaults


def test_save_config():
    """Test saving configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / CONFIG_FILE_NAME

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
