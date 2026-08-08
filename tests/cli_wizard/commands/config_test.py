# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for config commands."""

import json

import pytest
import yaml
from click.testing import CliRunner

from cli_wizard.commands.config import config
from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME

# Every way a config file can end up unloadable. Each one was reachable
# through `config set` or `config unset` before validation moved to the
# write path, and each one used to make every config command traceback.
CORRUPT_CONFIGS = {
    "unknown_key": "foo: bar\n",
    "null_non_optional": "ProjectName: null\n",
    "wrong_type": "JsonIndent: abc\n",
    "invalid_literal": "OutputFormat: xml\n",
    "invalid_hex_colour": "SplashColor: red\n",
    "not_a_mapping": "- a\n- b\n",
    "broken_yaml": "invalid: yaml: content:\n",
}

ALL_SUBCOMMANDS = [
    ["show"],
    ["get", "ProjectName"],
    ["set", "ProjectName", "Recovered"],
    ["unset", "ProjectName"],
    ["reset"],
]


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Point both config modules at a temporary config file."""
    path = tmp_path / CONFIG_FILE_NAME
    monkeypatch.setattr("cli_wizard.config.configuration.get_config_path", lambda: path)
    monkeypatch.setattr("cli_wizard.commands.config.get_config_path", lambda: path)
    return path


def stored(path):
    """Read the raw stored config, or an empty dict if the file is absent."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


class TestConfigGroup:
    """Tests for the config command group."""

    def test_group_help_lists_the_group_description(self):
        result = CliRunner().invoke(config, ["--help"])
        assert result.exit_code == 0
        assert "Manage configurations" in result.output


class TestConfigSet:
    """Tests for `config set`."""

    def test_persists_only_the_key_that_was_set(self, config_file):
        result = CliRunner().invoke(config, ["set", "ProjectName", "Alpha Tool"])
        assert result.exit_code == 0
        assert stored(config_file) == {"ProjectName": "Alpha Tool"}

    def test_reports_the_previous_effective_value(self, config_file):
        result = CliRunner().invoke(config, ["set", "ProjectName", "Alpha Tool"])
        assert json.loads(result.output)["oldValue"] == "My Project"

    @pytest.mark.parametrize(
        "key,raw,expected",
        [
            ("JsonIndent", "4", 4),
            ("Timeout", "60", 60),
            ("OutputColors", "false", False),
            ("RetryBackoffFactor", "1.5", 1.5),
            ("SplashColor", "#ffffff", "#FFFFFF"),
        ],
    )
    def test_coerces_the_value_before_storing_it(self, config_file, key, raw, expected):
        result = CliRunner().invoke(config, ["set", key, raw])
        assert result.exit_code == 0
        assert stored(config_file)[key] == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("users", ["users"]),
            ("users,admin", ["users", "admin"]),
            ("users, admin", ["users", "admin"]),
            ("users,", ["users"]),
            ("", []),
        ],
    )
    def test_splits_comma_separated_values_for_list_fields(
        self, config_file, raw, expected
    ):
        result = CliRunner().invoke(config, ["set", "IncludeTags", raw])
        assert result.exit_code == 0
        assert stored(config_file)["IncludeTags"] == expected

    def test_rejects_an_unknown_key_without_writing(self, config_file):
        result = CliRunner().invoke(config, ["set", "foo", "bar"])
        assert result.exit_code != 0
        assert "Unknown configuration key 'foo'" in result.output
        assert not config_file.exists()

    @pytest.mark.parametrize(
        "key,raw",
        [
            ("JsonIndent", "abc"),
            ("OutputFormat", "xml"),
            ("SplashColor", "red"),
            ("PackageName", "my-cli"),
            ("Timeout", "0"),
        ],
    )
    def test_rejects_an_invalid_value_without_writing(self, config_file, key, raw):
        result = CliRunner().invoke(config, ["set", key, raw])
        assert result.exit_code != 0
        assert f"Invalid value for '{key}'" in result.output
        assert not config_file.exists()

    def test_leaves_an_existing_good_config_untouched_when_rejecting(self, config_file):
        CliRunner().invoke(config, ["set", "ProjectName", "Alpha Tool"])
        before = config_file.read_text()

        result = CliRunner().invoke(config, ["set", "JsonIndent", "abc"])
        assert result.exit_code != 0
        assert config_file.read_text() == before

    @pytest.mark.parametrize("key", ["TagMapping", "CommandMapping"])
    def test_rejects_mapping_fields_with_a_clear_message(self, config_file, key):
        result = CliRunner().invoke(config, ["set", key, "a=b"])
        assert result.exit_code != 0
        assert "mapping and cannot be set from the command line" in result.output
        assert not config_file.exists()


class TestConfigDerivedValues:
    """Tests that derived fields keep tracking the fields they derive from."""

    def test_changing_project_name_rederives_dependent_values(self, config_file):
        runner = CliRunner()
        runner.invoke(config, ["set", "ProjectName", "Alpha Tool"])
        runner.invoke(config, ["set", "ProjectName", "Beta Tool"])

        result = runner.invoke(config, ["show"])
        shown = json.loads(result.output)
        assert shown["CommandName"] == "beta-tool"
        assert shown["PackageName"] == "beta_tool"
        assert shown["RepositoryUrl"].endswith("/beta-tool")

    def test_derived_values_are_not_written_to_the_config_file(self, config_file):
        CliRunner().invoke(config, ["set", "ProjectName", "Alpha Tool"])
        assert "CommandName" not in stored(config_file)
        assert "CopyrightYear" not in stored(config_file)

    def test_an_explicitly_set_derived_value_is_kept(self, config_file):
        runner = CliRunner()
        runner.invoke(config, ["set", "CommandName", "custom-name"])
        runner.invoke(config, ["set", "ProjectName", "Beta Tool"])

        shown = json.loads(runner.invoke(config, ["show"]).output)
        assert shown["CommandName"] == "custom-name"


class TestConfigGet:
    """Tests for `config get`."""

    def test_returns_the_effective_value(self, config_file):
        CliRunner().invoke(config, ["set", "ProjectName", "Alpha Tool"])
        result = CliRunner().invoke(config, ["get", "ProjectName"])
        assert result.exit_code == 0
        assert json.loads(result.output)["value"] == "Alpha Tool"

    def test_returns_the_default_for_a_key_that_was_never_set(self, config_file):
        result = CliRunner().invoke(config, ["get", "ProjectName"])
        assert result.exit_code == 0
        assert json.loads(result.output)["value"] == "My Project"

    def test_rejects_an_unknown_key(self, config_file):
        result = CliRunner().invoke(config, ["get", "nope"])
        assert result.exit_code != 0
        assert "Unknown configuration key 'nope'" in result.output


class TestConfigUnset:
    """Tests for `config unset`."""

    def test_removes_the_key_so_the_default_applies(self, config_file):
        runner = CliRunner()
        runner.invoke(config, ["set", "ProjectName", "Alpha Tool"])

        result = runner.invoke(config, ["unset", "ProjectName"])
        assert result.exit_code == 0
        assert "ProjectName" not in stored(config_file)
        assert json.loads(result.output)["value"] == "My Project"

    def test_reports_the_removed_value(self, config_file):
        runner = CliRunner()
        runner.invoke(config, ["set", "ProjectName", "Alpha Tool"])
        result = runner.invoke(config, ["unset", "ProjectName"])
        assert json.loads(result.output)["oldValue"] == "Alpha Tool"

    def test_unsetting_a_key_that_was_never_set_is_a_noop(self, config_file):
        result = CliRunner().invoke(config, ["unset", "ProjectName"])
        assert result.exit_code == 0
        assert json.loads(result.output)["value"] == "My Project"

    @pytest.mark.parametrize("key", ["ProjectName", "Version", "JsonIndent"])
    def test_never_leaves_a_config_the_schema_rejects(self, config_file, key):
        runner = CliRunner()
        runner.invoke(config, ["unset", key])
        # The file must still load, which is what the old None-writing
        # implementation could not guarantee.
        assert runner.invoke(config, ["show"]).exit_code == 0

    def test_rejects_an_unknown_key(self, config_file):
        result = CliRunner().invoke(config, ["unset", "nope"])
        assert result.exit_code != 0
        assert "Unknown configuration key 'nope'" in result.output


class TestConfigShow:
    """Tests for `config show`."""

    def test_outputs_the_full_effective_config(self, config_file):
        result = CliRunner().invoke(config, ["show"])
        assert result.exit_code == 0
        assert json.loads(result.output) == Config().model_dump()


class TestConfigReset:
    """Tests for `config reset`."""

    def test_deletes_the_config_file(self, config_file):
        config_file.write_text("ProjectName: Alpha Tool\n")
        result = CliRunner().invoke(config, ["reset"])
        assert result.exit_code == 0
        assert not config_file.exists()

    def test_succeeds_when_no_config_file_exists(self, config_file):
        result = CliRunner().invoke(config, ["reset"])
        assert result.exit_code == 0

    def test_outputs_the_defaults_it_reset_to(self, config_file):
        config_file.write_text("ProjectName: Alpha Tool\n")
        result = CliRunner().invoke(config, ["reset"])
        assert json.loads(result.output) == Config().model_dump()


class TestCorruptConfigRecovery:
    """Tests that a config file the schema rejects is never a dead end.

    This is the S3 regression: `config set` used to accept a value that made
    every subsequent command, `reset` included, exit with a traceback.
    """

    @pytest.mark.parametrize("content", CORRUPT_CONFIGS.values(), ids=CORRUPT_CONFIGS)
    @pytest.mark.parametrize("argv", ALL_SUBCOMMANDS, ids=lambda a: a[0])
    def test_every_subcommand_survives_a_corrupt_config(
        self, config_file, content, argv
    ):
        config_file.write_text(content)
        result = CliRunner().invoke(config, argv)
        assert result.exit_code == 0, result.output

    @pytest.mark.parametrize("content", CORRUPT_CONFIGS.values(), ids=CORRUPT_CONFIGS)
    def test_reset_recovers_from_a_corrupt_config(self, config_file, content):
        config_file.write_text(content)

        result = CliRunner().invoke(config, ["reset"])
        assert result.exit_code == 0
        assert not config_file.exists()
        assert CliRunner().invoke(config, ["show"]).exit_code == 0
