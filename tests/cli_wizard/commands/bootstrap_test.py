# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for bootstrap command."""

import json

import pytest
import yaml
from click.testing import CliRunner

from cli_wizard.cli import main
from cli_wizard.commands.bootstrap import (
    BOOTSTRAP_PARAMS,
    _generate_config_file,
    _get_default_for_param,
    _yaml_value,
)
from cli_wizard.config.schema import DEFAULT_PYTHON_VERSION

DEFAULT_ANSWERS = "\n" * len(BOOTSTRAP_PARAMS)

# A configuration file already in place when bootstrap runs
EXISTING_CONFIG = (
    'CommandName: "acme"\n'
    "IncludeGithubWorkflows: true\n"
    'DefaultBaseUrl: "https://api.example.com"\n'
)

# Values a prompt accepts that YAML would misread if written unescaped
HOSTILE_STRINGS = [
    pytest.param('My "cool" CLI', id="double_quotes"),
    pytest.param("C:\\path\\to", id="backslashes"),
    pytest.param('mix of \\ and "', id="backslash_and_quote"),
    pytest.param("key: value", id="colon"),
    pytest.param("  padded  ", id="surrounding_whitespace"),
    pytest.param("# not a comment", id="hash"),
    pytest.param("'single quoted'", id="single_quotes"),
    pytest.param("tab\tseparated", id="tab"),
    pytest.param("first\nsecond", id="newline"),
    pytest.param("{braces} [brackets] &anchor *alias", id="yaml_indicators"),
    pytest.param("ünïcode ✓", id="unicode"),
    pytest.param("x" * 200, id="long_value"),
    pytest.param("", id="empty"),
    pytest.param("true", id="ambiguous_boolean"),
]


class TestBootstrapCommand:
    """End-to-end tests for the bootstrap command."""

    def test_bootstrap_help(self):
        """Test bootstrap command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["bootstrap", "--help"])
        assert result.exit_code == 0
        assert "PATH" not in result.output
        assert "--output" in result.output
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
                "--output",
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
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
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
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS + "y\n",
        )

        assert result.exit_code == 0, result.output
        assert "already exists and is not empty" in result.output

    def test_bootstrap_prints_a_json_summary_on_stdout(self, tmp_path):
        """Test stdout holds one JSON document, the prompts having gone to stderr."""
        config_path = tmp_path / "cli-wizard.yaml"
        target_dir = tmp_path / "my-cli"

        result = CliRunner().invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        summary = json.loads(result.stdout)
        assert summary["output"] == str(target_dir)
        assert summary["configuration"] == str(config_path)
        assert summary["cliName"] == summary["packageName"].replace("_", "-")
        assert summary["nextCommand"].startswith("cli-wizard generate --configuration")
        assert "CLI command name" in result.stderr

    def test_bootstrap_directory_exists_nonempty_confirm_no(self, tmp_path):
        """Test bootstrap aborts when user declines to continue."""
        runner = CliRunner()
        target_dir = tmp_path / "existing-dir"
        target_dir.mkdir()
        (target_dir / "some-file.txt").write_text("hello")
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS + "n\n",
        )

        assert result.exit_code == 8  # Aborted
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
                "--output",
                str(target_dir),
                "--force",
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "already exists" not in result.output

    def test_bootstrap_declining_to_overwrite_the_config_writes_nothing(self, tmp_path):
        """Test bootstrap aborts before prompting when the overwrite is declined."""
        runner = CliRunner()
        target_dir = tmp_path / "my-cli"
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(EXISTING_CONFIG)

        result = runner.invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input="n\n",
        )

        assert result.exit_code == 8  # Aborted
        assert "already exists" in result.stderr
        assert "Project Configuration" not in result.stderr
        assert config_path.read_text() == EXISTING_CONFIG
        assert not target_dir.exists()

    @pytest.mark.parametrize(
        ("extra_args", "answers"),
        [([], "y\n" + DEFAULT_ANSWERS), (["--force"], DEFAULT_ANSWERS)],
        ids=["confirmed", "force"],
    )
    def test_bootstrap_overwrites_the_config_without_keeping_its_values(
        self, tmp_path, extra_args, answers
    ):
        """Test an overwritten config holds only the prompted values."""
        runner = CliRunner()
        target_dir = tmp_path / "my-cli"
        config_path = tmp_path / "cli-wizard.yaml"
        config_path.write_text(EXISTING_CONFIG)

        result = runner.invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
                *extra_args,
            ],
            input=answers,
        )

        assert result.exit_code == 0, result.output
        written = yaml.safe_load(config_path.read_text())
        assert written["CommandName"] == "my-cli"
        assert "IncludeGithubWorkflows" not in written
        assert "DefaultBaseUrl" not in written
        assert not (target_dir / ".github").exists()

    def test_bootstrap_default_configuration_path(self, tmp_path, monkeypatch):
        """Test bootstrap writes to ./cli-wizard.yaml without --configuration."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)
        target_dir = tmp_path / "my-cli"

        result = runner.invoke(
            main,
            ["bootstrap", "--output", str(target_dir)],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert (tmp_path / "cli-wizard.yaml").exists()

    def test_bootstrap_output_defaults_to_command_name_in_cwd(
        self, tmp_path, monkeypatch
    ):
        """Test that without --output the project lands in the cwd."""
        runner = CliRunner()
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        config_path = tmp_path / "nested" / "cli-wizard.yaml"
        answers = "pet-store\n" + "\n" * (len(BOOTSTRAP_PARAMS) - 1)

        result = runner.invoke(
            main,
            ["bootstrap", "--configuration", str(config_path)],
            input=answers,
        )

        assert result.exit_code == 0, result.output
        assert (work_dir / "pet-store" / "pyproject.toml").exists()
        assert not (tmp_path / "nested" / "pet-store").exists()
        assert "cli-wizard generate --configuration" in result.output
        assert "--output" not in result.output.split("Next steps")[1]

    def test_bootstrap_next_step_repeats_an_explicit_output(self, tmp_path):
        """Test that the suggested generate command keeps a non-default --output."""
        runner = CliRunner()
        target_dir = tmp_path / "elsewhere"
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert f"--output {target_dir}" in result.output

    def test_bootstrap_refuses_output_containing_the_config(self, tmp_path):
        """Test that the config file is never written inside the output directory."""
        runner = CliRunner()
        config_path = tmp_path / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            [
                "bootstrap",
                "--output",
                str(tmp_path),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 5  # OutputDirError
        assert "contains the configuration file" in result.output
        assert not config_path.exists()

    def test_command_name_defaults_to_the_config_directory_without_output(
        self, tmp_path, monkeypatch
    ):
        """Test that the CommandName prompt defaults to the config file's directory."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "Pet Store" / "cli-wizard.yaml"

        result = runner.invoke(
            main,
            ["bootstrap", "--configuration", str(config_path)],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output
        assert "CLI command name" in result.output
        assert "[pet-store]:" in result.output

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
                "--output",
                str(target_dir),
                "--configuration",
                str(config_path),
            ],
            input=DEFAULT_ANSWERS,
        )

        assert result.exit_code == 0, result.output


class TestGetDefaultForParam:
    """Tests for _get_default_for_param helper."""

    def test_command_name_derived_from_target_dir(self):
        """CommandName defaults to kebab-case of the target directory name."""
        default = _get_default_for_param(
            "CommandName", {"_target_dir_name": "My Cool CLI"}
        )
        assert default == "my-cool-cli"

    def test_project_name_derived_from_command_name(self):
        """ProjectName defaults to title case of CommandName."""
        default = _get_default_for_param("ProjectName", {"CommandName": "my-cool-cli"})
        assert default == "My Cool Cli"

    def test_package_name_derived_from_command_name(self):
        """PackageName defaults to snake_case of CommandName."""
        default = _get_default_for_param("PackageName", {"CommandName": "my-cool-cli"})
        assert default == "my_cool_cli"

    def test_github_user_defaults_to_system_user(self, monkeypatch):
        """GithubUser defaults to the current system username."""
        monkeypatch.setattr("getpass.getuser", lambda: "testuser")
        default = _get_default_for_param("GithubUser", {})
        assert default == "testuser"

    def test_copyright_year_defaults_to_current_year(self):
        """CopyrightYear defaults to the current year."""
        from datetime import date

        default = _get_default_for_param("CopyrightYear", {})
        assert default == str(date.today().year)

    def test_repository_url_derived_from_github_user_and_command_name(self):
        """RepositoryUrl defaults to a GitHub URL built from GithubUser/CommandName."""
        default = _get_default_for_param(
            "RepositoryUrl",
            {"GithubUser": "octocat", "CommandName": "my-cli"},
        )
        assert default == "https://github.com/octocat/my-cli"

    def test_home_page_url_defaults_to_the_repository_url(self):
        """HomePageUrl defaults to the RepositoryUrl prompted just before it."""
        default = _get_default_for_param(
            "HomePageUrl",
            {"RepositoryUrl": "https://github.com/octocat/my-cli"},
        )
        assert default == "https://github.com/octocat/my-cli"

    def test_falls_back_to_schema_default(self):
        """Unrecognized params fall back to the schema default value."""
        default = _get_default_for_param("PythonVersion", {})
        assert default == DEFAULT_PYTHON_VERSION


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

    @pytest.mark.parametrize("value", HOSTILE_STRINGS)
    def test_string_round_trips_through_yaml(self, value):
        assert yaml.safe_load(f"Key: {_yaml_value(value)}") == {"Key": value}

    def test_string_is_written_on_a_single_line(self):
        assert "\n" not in _yaml_value("first\nsecond " + "x" * 200)


class TestGenerateConfigFile:
    """Tests for _generate_config_file helper."""

    @pytest.mark.parametrize("value", HOSTILE_STRINGS)
    def test_prompted_values_round_trip(self, tmp_path, value):
        config_path = tmp_path / "cli-wizard.yaml"
        prompted = {param: value for param in BOOTSTRAP_PARAMS}

        _generate_config_file(config_path, prompted)

        loaded = yaml.safe_load(config_path.read_text())
        assert {param: loaded[param] for param in BOOTSTRAP_PARAMS} == prompted
