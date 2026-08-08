# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for generate command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from cli_wizard.cli import main
from cli_wizard.commands.generate import _expand_config_references
from cli_wizard.generator.generator import RuffNotFoundError


def create_test_files(temp_dir: Path, cli_name: str = "test-cli") -> tuple[Path, Path]:
    """Create test OpenAPI spec and config files."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List users",
                    "tags": ["Users"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    config = {
        # Let the schema derive CommandName (kebab-case) and PackageName
        # (snake_case) from ProjectName. Setting PackageName directly to a
        # kebab-case name produces an invalid Python package.
        "ProjectName": cli_name,
        "DefaultBaseUrl": "https://api.example.com",
        "ExcludeTags": [],
        "IncludeTags": [],
    }

    openapi_path = temp_dir / "openapi.json"
    config_path = temp_dir / "cli-wizard.yaml"

    with open(openapi_path, "w") as f:
        json.dump(openapi_spec, f)

    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return openapi_path, config_path


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_help(self):
        """Test generate command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--api" in result.output or "-a" in result.output
        assert "--configuration" in result.output or "-c" in result.output
        assert "PATH" in result.output

    def test_generate_missing_openapi(self):
        """Test generate with missing OpenAPI file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )
            output_dir = Path(temp_dir) / "output"

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    "nonexistent.yaml",
                    "--configuration",
                    str(config_path),
                ],
            )
            # Click validates file existence with exists=True, returns exit code 2
            assert result.exit_code == 2

    def test_generate_missing_config(self):
        """Test generate with missing config file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            openapi_path = Path(temp_dir) / "openapi.json"
            openapi_path.write_text('{"openapi": "3.0.0", "paths": {}}')
            output_dir = Path(temp_dir) / "output"

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    "nonexistent.yaml",
                ],
            )
            # Click validates file existence with exists=True, returns exit code 2
            assert result.exit_code == 2

    def test_generate_success(self):
        """Test successful CLI generation."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "Generated CLI" in result.output
            assert (output_dir / "pyproject.toml").exists()

    def test_generate_with_custom_name_in_config(self):
        """Test generate with custom CLI name from config."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(
                temp_path, cli_name="my-custom-cli"
            )
            output_dir = temp_path / "output"

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "my-custom-cli" in result.output

            pyproject = (output_dir / "pyproject.toml").read_text()
            assert "my-custom-cli" in pyproject

    def test_generate_with_working_dir(self):
        """Test generate uses resolved paths correctly."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "my-output"

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert (output_dir / "pyproject.toml").exists()

    def test_generate_empty_spec(self):
        """Test generate with empty OpenAPI spec (no operations)."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            openapi_path = temp_path / "openapi.json"
            openapi_path.write_text(
                json.dumps(
                    {
                        "openapi": "3.0.0",
                        "info": {"title": "Test", "version": "1.0"},
                        "paths": {},
                    }
                )
            )

            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            # Empty spec generates CLI without API commands (warning only)
            assert result.exit_code == 0
            assert "No operations found" in result.output

    def test_generate_yaml_openapi(self):
        """Test generate with YAML OpenAPI spec."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            openapi_spec = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {
                    "/items": {
                        "get": {
                            "operationId": "listItems",
                            "tags": ["Items"],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }

            openapi_path = temp_path / "openapi.yaml"
            with open(openapi_path, "w") as f:
                yaml.dump(openapi_spec, f)

            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "Generated CLI" in result.output

    def test_generate_with_debug(self):
        """Test generate with debug flag."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"

            result = runner.invoke(
                main,
                [
                    "--debug",
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0

    def test_generate_no_api_no_openapi_spec(self):
        """Test generate without --api and without OpenapiSpec in config."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "No OpenAPI spec provided" in result.output

    def test_generate_openapi_spec_from_config(self):
        """Test generate resolves OpenapiSpec from config relative to config dir."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, _ = create_test_files(temp_path)

            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\n"
                "DefaultBaseUrl: https://api.example.com\n"
                "OpenapiSpec: openapi.json\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "Parsing OpenAPI spec" in result.output

    def test_generate_openapi_spec_from_config_missing(self):
        """Test generate warns when configured OpenapiSpec file is missing."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\n"
                "DefaultBaseUrl: https://api.example.com\n"
                "OpenapiSpec: missing.json\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_generate_cleans_existing_output_directory(self):
        """Test generate removes a pre-existing output directory before writing."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"
            output_dir.mkdir()
            (output_dir / "stale-file.txt").write_text("stale")

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--force",
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 0
            assert "Cleaning output directory" in result.output
            assert not (output_dir / "stale-file.txt").exists()

    def test_generate_confirms_before_deleting_non_empty_output(self):
        """Test generate asks before deleting a non-empty output directory."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"
            output_dir.mkdir()
            (output_dir / "stale-file.txt").write_text("stale")

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
                input="y\n",
            )
            assert result.exit_code == 0
            assert str(output_dir) in result.output
            assert "entire contents will be deleted" in result.output
            assert not (output_dir / "stale-file.txt").exists()

    def test_generate_declined_confirmation_leaves_output_untouched(self):
        """Test declining the confirmation aborts without deleting anything."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"
            output_dir.mkdir()
            marker = output_dir / "marker.txt"
            marker.write_text("keep me")

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
                input="n\n",
            )
            assert result.exit_code != 0
            assert marker.exists(), "output was deleted despite declining"
            assert marker.read_text() == "keep me"

    def test_generate_non_empty_output_aborts_without_confirmation(self):
        """Test generate aborts when it cannot prompt and --force is absent."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"
            output_dir.mkdir()
            marker = output_dir / "marker.txt"
            marker.write_text("keep me")

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
                input="",
            )
            assert result.exit_code != 0
            assert marker.exists(), "output was deleted without confirmation"

    def test_generate_empty_output_directory_does_not_prompt(self):
        """Test an existing but empty output directory proceeds without asking."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)
            output_dir = temp_path / "output"
            output_dir.mkdir()

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(output_dir),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
                input="",
            )
            assert result.exit_code == 0
            assert "entire contents will be deleted" not in result.output

    def test_generate_output_dir_is_cwd_fails(self):
        """Test generate refuses to clean the output directory when it is cwd."""
        runner = CliRunner()
        with runner.isolated_filesystem() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)

            result = runner.invoke(
                main,
                [
                    "generate",
                    ".",
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 1
            assert "Cannot clean output directory" in result.output

    def test_generate_invalid_field_value(self):
        """Test generate with a syntactically valid but semantically invalid config."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, _ = create_test_files(temp_path)

            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\n"
                "DefaultBaseUrl: https://api.example.com\n"
                "OutputFormat: xml\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 1
            assert "Invalid configuration" in result.output

    def test_generate_invalid_config_yaml(self):
        """Test generate with invalid config YAML."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            openapi_spec = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {
                    "/items": {
                        "get": {
                            "operationId": "listItems",
                            "tags": ["Items"],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }

            openapi_path = temp_path / "openapi.json"
            with open(openapi_path, "w") as f:
                json.dump(openapi_spec, f)

            # Create invalid YAML config (syntax error)
            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text("invalid: yaml: content:")

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            # Should fail with invalid config (missing required fields)
            assert result.exit_code == 1
            assert (
                "Invalid configuration" in result.output
                or "Could not load config" in result.output
            )

    def test_existing_output_survives_missing_ruff(self):
        """Test that a missing ruff does not delete the previous output."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)

            output_dir = temp_path / "output"
            output_dir.mkdir()
            marker = output_dir / "marker.txt"
            marker.write_text("keep me")

            with patch(
                "cli_wizard.commands.generate.resolve_ruff",
                side_effect=RuffNotFoundError("ruff not found"),
            ):
                result = runner.invoke(
                    main,
                    [
                        "generate",
                        str(output_dir),
                        "--api",
                        str(openapi_path),
                        "--configuration",
                        str(config_path),
                    ],
                )

            assert result.exit_code == 1
            assert marker.exists(), "previous output was deleted despite the abort"
            assert marker.read_text() == "keep me"

    def test_generate_circular_config_reference(self):
        """Test generate with a config value that references itself."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, _ = create_test_files(temp_path)

            config_path = temp_path / "cli-wizard.yaml"
            config_path.write_text(
                "PackageName: test\n"
                "DefaultBaseUrl: https://api.example.com\n"
                'MainDir: "#[MainDir]/x"\n'
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    str(temp_path / "output"),
                    "--api",
                    str(openapi_path),
                    "--configuration",
                    str(config_path),
                ],
            )
            assert result.exit_code == 1
            assert "MainDir" in result.output


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
