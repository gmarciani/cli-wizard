# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for loading the generation configuration."""

import pytest

from cli_wizard.config.project import expand_config_references, load_cli_config
from cli_wizard.errors import ConfigError


class TestExpandConfigReferences:
    """Tests for expand_config_references helper."""

    def test_simple_reference(self):
        config = {"A": "x", "B": "#[A]-y"}
        result = expand_config_references(config)
        assert result["B"] == "x-y"

    def test_unresolved_reference_left_as_is(self):
        config = {"B": "#[Missing]-y"}
        result = expand_config_references(config)
        assert result["B"] == "#[Missing]-y"

    def test_nested_dict_and_list_expansion(self):
        config = {
            "A": "x",
            "nested": {"key": "#[A]-nested"},
            "items": ["#[A]-1", "#[A]-2"],
        }
        result = expand_config_references(config)
        assert result["nested"]["key"] == "x-nested"
        assert result["items"] == ["x-1", "x-2"]

    def test_non_string_value_unchanged(self):
        config = {"Count": 5}
        result = expand_config_references(config)
        assert result["Count"] == 5

    def test_nested_reference_chain_resolves(self):
        config = {
            "CommandName": "mycli",
            "MainDir": "${HOME}/.#[CommandName]",
            "ProfileFile": "#[MainDir]/profiles.yaml",
        }
        result = expand_config_references(config)
        assert result["MainDir"] == "${HOME}/.mycli"
        assert result["ProfileFile"] == "${HOME}/.mycli/profiles.yaml"

    @pytest.mark.parametrize(
        "config",
        [
            pytest.param({"A": "#[A]/x"}, id="self_reference"),
            pytest.param({"A": "#[B]", "B": "#[A]"}, id="mutual_cycle"),
            pytest.param({"A": "#[B]", "B": "#[C]", "C": "#[A]"}, id="indirect_cycle"),
            pytest.param(
                {"A": "#[A]", "nested": {"key": "#[A]"}}, id="cycle_reached_from_nested"
            ),
        ],
    )
    def test_circular_reference_raises(self, config):
        with pytest.raises(ValueError, match="[Cc]ircular"):
            expand_config_references(config)

    def test_circular_reference_error_names_offending_value(self):
        with pytest.raises(ValueError) as excinfo:
            expand_config_references({"MainDir": "#[MainDir]/x"})
        assert "MainDir" in str(excinfo.value)
        assert "#[MainDir]/x" in str(excinfo.value)


class TestLoadCliConfig:
    """Tests for load_cli_config helper."""

    def test_valid_config(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(
            "PackageName: my_cli\nDefaultBaseUrl: https://api.example.com\n"
        )
        config = load_cli_config(config_path)
        assert config["PackageName"] == "my_cli"

    def test_invalid_yaml_exits(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text("key: [unbalanced")
        with pytest.raises(ConfigError, match="Could not load config file"):
            load_cli_config(config_path)

    def test_validation_error_exits(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(
            "PackageName: my_cli\n"
            "DefaultBaseUrl: https://api.example.com\n"
            "OutputFormat: xml\n"
        )
        with pytest.raises(ConfigError, match="OutputFormat"):
            load_cli_config(config_path)

    def test_circular_reference_exits(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text('PackageName: my_cli\nMainDir: "#[MainDir]/x"\n')
        with pytest.raises(ConfigError, match="MainDir"):
            load_cli_config(config_path)
