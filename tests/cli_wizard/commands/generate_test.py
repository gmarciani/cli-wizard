# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for generate command."""

import json
import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from cli_wizard.cli import main


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
        "PackageName": cli_name,
        "DefaultBaseUrl": "https://api.example.com",
        "ExcludeTags": [],
        "IncludeTags": [],
    }

    openapi_path = temp_dir / "openapi.json"
    config_path = temp_dir / "config.yaml"

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
        assert "--openapi" in result.output
        assert "--config" in result.output
        assert "--output" in result.output
        assert "--working-dir" in result.output

    def test_generate_missing_openapi(self):
        """Test generate with missing OpenAPI file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--openapi",
                    "nonexistent.yaml",
                    "--config",
                    str(config_path),
                ],
            )
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_generate_missing_config(self):
        """Test generate with missing config file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            openapi_path = Path(temp_dir) / "openapi.json"
            openapi_path.write_text('{"openapi": "3.0.0", "paths": {}}')

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    "nonexistent.yaml",
                ],
            )
            assert result.exit_code == 1
            assert "not found" in result.output

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
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_dir),
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
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_dir),
                ],
            )
            assert result.exit_code == 0
            assert "my-custom-cli" in result.output

            pyproject = (output_dir / "pyproject.toml").read_text()
            assert "my-custom-cli" in pyproject

    def test_generate_with_working_dir(self):
        """Test generate with working directory option."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            openapi_path, config_path = create_test_files(temp_path)

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--working-dir",
                    str(temp_path),
                    "--openapi",
                    "openapi.json",
                    "--config",
                    "config.yaml",
                    "--output",
                    "my-output",
                ],
            )
            assert result.exit_code == 0
            assert (temp_path / "my-output" / "pyproject.toml").exists()

    def test_generate_empty_spec(self):
        """Test generate with empty OpenAPI spec."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            openapi_path = temp_path / "openapi.json"
            openapi_path.write_text(
                '{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}, "paths": {}}'
            )

            config_path = temp_path / "config.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(temp_path / "output"),
                ],
            )
            assert result.exit_code == 1
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

            config_path = temp_path / "config.yaml"
            config_path.write_text(
                "PackageName: test\nDefaultBaseUrl: https://api.example.com\n"
            )

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(temp_path / "output"),
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
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_dir),
                ],
            )
            assert result.exit_code == 0

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
            config_path = temp_path / "config.yaml"
            config_path.write_text("invalid: yaml: content:")

            result = runner.invoke(
                main,
                [
                    "generate",
                    "--openapi",
                    str(openapi_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(temp_path / "output"),
                ],
            )
            # Should fail with invalid config (missing required fields)
            assert result.exit_code == 1
            assert (
                "Invalid configuration" in result.output
                or "Could not load config" in result.output
            )
