# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for bootstrap command."""

import pytest
from click.testing import CliRunner

from cli_wizard.cli import main
from cli_wizard.commands.bootstrap import (
    BOOTSTRAP_PARAMS,
    _expand_config_references,
    _get_default_for_param,
    _load_cli_config,
    _load_existing_config,
    _yaml_value,
)

DEFAULT_ANSWERS = "\n" * len(BOOTSTRAP_PARAMS)


class TestBootstrapCommand:
    """End-to-end tests for the bootstrap command."""

    def test_bootstrap_help(self):
        """Test bootstrap command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["bootstrap", "--help"])
        assert result.exit_code == 0
        assert "PATH" in result.output
        assert "--force" in result.output
        assert "--configuration" in result.output

    def test_bootstrap_new_project(self, tmp_path):
        """Test bootstrapping a project in a directory that does not exist yet."""
        runner = CliRunner()
        target_dir = tmp_path / "my-new-cli"
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "bootstrap",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "bootstrapped successfully" in result.output
        assert config_path.exists()
        assert (target_dir / "pyproject.toml").exists()

    def test_bootstrap_directory_exists_empty(self, tmp_path):
        """Test bootstrap when target directory exists but is empty."""
        runner = CliRunner()
        target_dir = tmp_path / "empty-dir"
        target_dir.mkdir()
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            ["bootstrap", str(target_dir), "--configuration", str(config_path)],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output

    def test_bootstrap_directory_exists_nonempty_confirm_yes(self, tmp_path):
        """Test bootstrap prompts for confirmation and continues on yes."""
        runner = CliRunner()
        target_dir = tmp_path / "existing-dir"
        target_dir.mkdir()
        (target_dir / "some-file.txt").write_text("hello")
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            ["bootstrap", str(target_dir), "--configuration", str(config_path)],
            input="y\n" + DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "already exists and is not empty" in result.output

    def test_bootstrap_directory_exists_nonempty_confirm_no(self, tmp_path):
        """Test bootstrap aborts when user declines to continue."""
        runner = CliRunner()
        target_dir = tmp_path / "existing-dir"
        target_dir.mkdir()
        (target_dir / "some-file.txt").write_text("hello")
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            ["bootstrap", str(target_dir), "--configuration", str(config_path)],
            input="n\n",
        )

        assert result.exit_code == 1
        assert "Aborted" in result.output
        assert not config_path.exists()

    def test_bootstrap_directory_exists_nonempty_with_force(self, tmp_path):
        """Test bootstrap skips confirmation with --force."""
        runner = CliRunner()
        target_dir = tmp_path / "existing-dir"
        target_dir.mkdir()
        (target_dir / "some-file.txt").write_text("hello")
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "bootstrap",
                str(target_dir),
                "--force",
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "already exists" not in result.output

    def test_bootstrap_with_existing_config(self, tmp_path):
        """Test bootstrap reuses values from an existing config file as defaults."""
        runner = CliRunner()
        target_dir = tmp_path / "my-cli"
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(
            "CommandName: my-existing-cli\nDefaultBaseUrl: https://api.example.com\n"
        )

        result = runner.invoke(
            main,
            ["bootstrap", str(target_dir), "--configuration", str(config_path)],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "Using existing config" in result.output
        assert "my-existing-cli" in config_path.read_text()

    def test_bootstrap_default_configuration_path(self, tmp_path, monkeypatch):
        """Test bootstrap writes to ./cli-wizard.yaml without --configuration."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)
        target_dir = tmp_path / "my-cli"

        result = runner.invoke(
            main,
            ["bootstrap", str(target_dir)],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert (tmp_path / "cli-wizard.yaml").exists()

    def test_bootstrap_with_debug(self, tmp_path):
        """Test bootstrap with --debug flag enabled."""
        runner = CliRunner()
        target_dir = tmp_path / "my-cli"
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "--debug",
                "bootstrap",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output


class TestGetDefaultForParam:
    """Tests for _get_default_for_param helper."""

    def test_existing_config_takes_priority(self):
        """Existing config values take priority over derived/schema defaults."""
        default = _get_default_for_param(
            "CommandName", {}, existing_config={"CommandName": "from-config"}
        )
        assert default == "from-config"

    def test_command_name_derived_from_target_dir(self):
        """CommandName defaults to kebab-case of the target directory name."""
        default = _get_default_for_param(
            "CommandName", {"_target_dir_name": "My Cool CLI"}, None
        )
        assert default == "my-cool-cli"

    def test_project_name_derived_from_command_name(self):
        """ProjectName defaults to title case of CommandName."""
        default = _get_default_for_param(
            "ProjectName", {"CommandName": "my-cool-cli"}, None
        )
        assert default == "My Cool Cli"

    def test_package_name_derived_from_command_name(self):
        """PackageName defaults to snake_case of CommandName."""
        default = _get_default_for_param(
            "PackageName", {"CommandName": "my-cool-cli"}, None
        )
        assert default == "my_cool_cli"

    def test_github_user_defaults_to_system_user(self, monkeypatch):
        """GithubUser defaults to the current system username."""
        monkeypatch.setattr("getpass.getuser", lambda: "testuser")
        default = _get_default_for_param("GithubUser", {}, None)
        assert default == "testuser"

    def test_copyright_year_defaults_to_current_year(self):
        """CopyrightYear defaults to the current year."""
        from datetime import date

        default = _get_default_for_param("CopyrightYear", {}, None)
        assert default == str(date.today().year)

    def test_repository_url_derived_from_github_user_and_command_name(self):
        """RepositoryUrl defaults to a GitHub URL built from GithubUser/CommandName."""
        default = _get_default_for_param(
            "RepositoryUrl",
            {"GithubUser": "octocat", "CommandName": "my-cli"},
            None,
        )
        assert default == "https://github.com/octocat/my-cli"

    def test_falls_back_to_schema_default(self):
        """Unrecognized params fall back to the schema default value."""
        default = _get_default_for_param("PythonVersion", {}, None)
        assert default == "3.12"


class TestLoadExistingConfig:
    """Tests for _load_existing_config helper."""

    def test_missing_file_returns_none(self, tmp_path):
        """Test that a missing config file returns None."""
        assert _load_existing_config(tmp_path / "nonexistent.yaml") is None

    def test_valid_config_returns_dict(self, tmp_path):
        """Test that a valid config file is parsed into a dict."""
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text("CommandName: my-cli\n")
        assert _load_existing_config(config_path) == {"CommandName": "my-cli"}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        """Test that an empty config file returns an empty dict."""
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text("")
        assert _load_existing_config(config_path) == {}

    def test_invalid_yaml_returns_none(self, tmp_path):
        """Test that invalid YAML content returns None."""
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text("key: [unbalanced")
        assert _load_existing_config(config_path) is None


class TestYamlValue:
    """Tests for _yaml_value helper."""

    def test_none(self):
        assert _yaml_value(None) == "null"

    def test_booleans(self):
        assert _yaml_value(True) == "true"
        assert _yaml_value(False) == "false"

    def test_ambiguous_string(self):
        assert _yaml_value("true") == '"true"'
        assert _yaml_value("") == '""'

    def test_string_with_special_characters(self):
        assert _yaml_value("a:b") == '"a:b"'

    def test_plain_string(self):
        assert _yaml_value("hello") == '"hello"'

    def test_numbers(self):
        assert _yaml_value(42) == "42"
        assert _yaml_value(0.5) == "0.5"

    def test_empty_list(self):
        assert _yaml_value([]) == "[]"

    def test_nonempty_list(self):
        assert _yaml_value(["a", 1, None]) == '["a", 1, null]'

    def test_empty_dict(self):
        assert _yaml_value({}) == "{}"

    def test_nonempty_dict(self):
        assert _yaml_value({"a": "b"}) == '{a: "b"}'

    def test_fallback_repr(self):
        assert _yaml_value((1, 2)) == str((1, 2))


class TestExpandConfigReferences:
    """Tests for _expand_config_references helper."""

    def test_simple_reference(self):
        config = {"A": "x", "B": "#[A]-y"}
        result = _expand_config_references(config)
        assert result["B"] == "x-y"

    def test_unresolved_reference_left_as_is(self):
        config = {"B": "#[Missing]-y"}
        result = _expand_config_references(config)
        assert result["B"] == "#[Missing]-y"

    def test_nested_dict_and_list_expansion(self):
        config = {
            "A": "x",
            "nested": {"key": "#[A]-nested"},
            "items": ["#[A]-1", "#[A]-2"],
        }
        result = _expand_config_references(config)
        assert result["nested"]["key"] == "x-nested"
        assert result["items"] == ["x-1", "x-2"]

    def test_non_string_value_unchanged(self):
        config = {"Count": 5}
        result = _expand_config_references(config)
        assert result["Count"] == 5

    def test_nested_reference_chain_resolves(self):
        config = {
            "CommandName": "mycli",
            "MainDir": "${HOME}/.#[CommandName]",
            "ProfileFile": "#[MainDir]/profiles.yaml",
        }
        result = _expand_config_references(config)
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
            _expand_config_references(config)

    def test_circular_reference_error_names_offending_value(self):
        with pytest.raises(ValueError) as excinfo:
            _expand_config_references({"MainDir": "#[MainDir]/x"})
        assert "MainDir" in str(excinfo.value)
        assert "#[MainDir]/x" in str(excinfo.value)


class TestLoadCliConfig:
    """Tests for _load_cli_config helper."""

    def test_valid_config(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(
            "PackageName: my_cli\nDefaultBaseUrl: https://api.example.com\n"
        )
        config = _load_cli_config(config_path)
        assert config["PackageName"] == "my_cli"

    def test_invalid_yaml_exits(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text("key: [unbalanced")
        with pytest.raises(SystemExit):
            _load_cli_config(config_path)

    def test_validation_error_exits(self, tmp_path):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(
            "PackageName: my_cli\n"
            "DefaultBaseUrl: https://api.example.com\n"
            "OutputFormat: xml\n"
        )
        with pytest.raises(SystemExit):
            _load_cli_config(config_path)

    def test_circular_reference_exits(self, tmp_path, capsys):
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text('PackageName: my_cli\nMainDir: "#[MainDir]/x"\n')
        with pytest.raises(SystemExit):
            _load_cli_config(config_path)
        assert "MainDir" in capsys.readouterr().err
