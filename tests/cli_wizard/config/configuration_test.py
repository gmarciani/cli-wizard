# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for configuration utilities."""

import logging

import pytest
import yaml
from pydantic import ValidationError

from cli_wizard.config.configuration import (
    get_config_path,
    load_config,
    load_stored_config,
    save_config,
)
from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    """Point the configuration module at a temporary config file."""
    path = tmp_path / CONFIG_FILE_NAME
    monkeypatch.setattr("cli_wizard.config.configuration.get_config_path", lambda: path)
    return path


def test_get_config_path():
    """Test getting config path."""
    path = get_config_path()
    assert path.name == CONFIG_FILE_NAME
    assert ".cli_wizard" in str(path)


def test_load_config_no_user_config(config_path):
    """Test loading config when no user config exists returns schema defaults."""
    assert load_config() == Config().model_dump()


def test_load_config_with_user_config(config_path):
    """Test loading config with user config file."""
    config_path.write_text("CommandName: my-cli\nPackageName: my_cli\n")

    config = load_config()
    assert config["CommandName"] == "my-cli"
    assert config["PackageName"] == "my_cli"
    assert "ProjectName" in config


def test_load_config_user_overrides_default(config_path):
    """Test that user config overrides schema defaults."""
    config_path.write_text("Version: 2.0.0\n")
    assert load_config()["Version"] == "2.0.0"


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("invalid: yaml: content:\n", id="broken_yaml"),
        pytest.param("- item1\n- item2\n", id="not_a_mapping"),
        pytest.param("foo: bar\n", id="unknown_key"),
        pytest.param("ProjectName: null\n", id="null_non_optional"),
        pytest.param("JsonIndent: abc\n", id="wrong_type"),
        pytest.param("OutputFormat: xml\n", id="invalid_literal"),
    ],
)
def test_load_config_falls_back_to_defaults_for_unusable_files(config_path, content):
    """An unusable config file degrades to defaults rather than raising."""
    config_path.write_text(content)
    assert load_config() == Config().model_dump()


def test_load_config_warns_when_falling_back(config_path, caplog):
    """Falling back is visible, not silent."""
    config_path.write_text("foo: bar\n")

    with caplog.at_level(logging.WARNING):
        load_config()

    assert any(
        "Ignoring invalid configuration file" in record.message
        for record in caplog.records
    )


def test_load_stored_config_returns_only_stored_keys(config_path):
    """Stored config carries what the user set, not the merged defaults."""
    config_path.write_text("ProjectName: Alpha Tool\n")
    assert load_stored_config() == {"ProjectName": "Alpha Tool"}


def test_load_stored_config_is_empty_without_a_file(config_path):
    """A missing config file reads as an empty stored config."""
    assert load_stored_config() == {}


def test_save_config_round_trips(config_path):
    """Test saving configuration."""
    save_config({"ProjectName": "Alpha Tool", "JsonIndent": 4})

    assert config_path.exists()
    assert yaml.safe_load(config_path.read_text()) == {
        "ProjectName": "Alpha Tool",
        "JsonIndent": 4,
    }


def test_save_config_persists_only_the_given_keys(config_path):
    """Derived and default values must not be frozen into the file."""
    save_config({"ProjectName": "Alpha Tool"})

    saved = yaml.safe_load(config_path.read_text())
    assert saved == {"ProjectName": "Alpha Tool"}


def test_save_config_coerces_values_to_schema_types(config_path):
    """Values arrive from the CLI as strings and are stored as schema types."""
    save_config({"JsonIndent": "4", "OutputColors": "false"})

    saved = yaml.safe_load(config_path.read_text())
    assert saved["JsonIndent"] == 4
    assert saved["OutputColors"] is False


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({"foo": "bar"}, id="unknown_key"),
        pytest.param({"JsonIndent": "abc"}, id="wrong_type"),
        pytest.param({"OutputFormat": "xml"}, id="invalid_literal"),
        pytest.param({"PackageName": "my-cli"}, id="invalid_identifier"),
    ],
)
def test_save_config_rejects_invalid_config(config_path, config):
    """Validation happens on the way in, so the file cannot go bad."""
    with pytest.raises(ValidationError):
        save_config(config)

    assert not config_path.exists()


def test_save_config_leaves_a_good_file_intact_when_rejecting(config_path):
    """A rejected write must not damage the config already on disk."""
    save_config({"ProjectName": "Alpha Tool"})
    before = config_path.read_text()

    with pytest.raises(ValidationError):
        save_config({"ProjectName": "Alpha Tool", "JsonIndent": "abc"})

    assert config_path.read_text() == before
