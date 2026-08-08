# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for CLI generator."""

import ast
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cli_wizard.generator.generator import (
    RUFF_COMMANDS,
    CliGenerator,
    RuffNotFoundError,
    _build_url_path,
    resolve_ruff,
)
from cli_wizard.generator.models import (
    CommandGroup,
    Operation,
    Parameter,
    RequestBodyProperty,
)


class TestBuildUrlPath:
    """Tests for _build_url_path helper."""

    def test_no_path_params(self):
        """Test URL path without parameters."""
        op = Operation(
            operation_id="listUsers",
            method="GET",
            path="/users",
            summary="List users",
            description="",
            tags=["Users"],
            parameters=[],
        )
        assert _build_url_path(op) == "/users"

    def test_single_path_param(self):
        """Test URL path with single parameter."""
        op = Operation(
            operation_id="getUser",
            method="GET",
            path="/users/{userId}",
            summary="Get user",
            description="",
            tags=["Users"],
            parameters=[
                Parameter(
                    name="userId",
                    location="path",
                    param_type="string",
                    required=True,
                )
            ],
        )
        assert _build_url_path(op) == "/users/{user_id}"

    def test_multiple_path_params(self):
        """Test URL path with multiple parameters."""
        op = Operation(
            operation_id="getOrderItem",
            method="GET",
            path="/orders/{orderId}/items/{itemId}",
            summary="Get order item",
            description="",
            tags=["Orders"],
            parameters=[
                Parameter(
                    name="orderId",
                    location="path",
                    param_type="string",
                    required=True,
                ),
                Parameter(
                    name="itemId",
                    location="path",
                    param_type="string",
                    required=True,
                ),
            ],
        )
        assert _build_url_path(op) == "/orders/{order_id}/items/{item_id}"

    def test_query_params_ignored(self):
        """Test that query parameters don't affect URL path."""
        op = Operation(
            operation_id="listUsers",
            method="GET",
            path="/users",
            summary="List users",
            description="",
            tags=["Users"],
            parameters=[
                Parameter(
                    name="limit",
                    location="query",
                    param_type="integer",
                    required=False,
                )
            ],
        )
        assert _build_url_path(op) == "/users"


class TestCliGenerator:
    """Tests for CliGenerator."""

    def _default_config(
        self, cli_name: str = "test-cli", package_name: str = "test_cli"
    ) -> dict:
        """Create a default config for testing."""
        return {
            "CommandName": cli_name,
            "PackageName": package_name,
            "Description": "A test CLI",
            "AuthorName": "Test Author",
            "AuthorEmail": "test@example.com",
            "PythonVersion": "3.12",
            "DefaultBaseUrl": "http://localhost:3000",
            "Timeout": 30,
            "RepositoryUrl": "https://github.com/test/test-cli",
        }

    def test_generate_creates_project_structure(self):
        """Test that generate creates the expected project structure."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[
                    Operation(
                        operation_id="listUsers",
                        method="GET",
                        path="/users",
                        summary="List users",
                        description="",
                        tags=["Users"],
                        parameters=[],
                    )
                ],
            )
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            # Check project files
            assert (output_dir / "pyproject.toml").exists()
            assert (output_dir / "README.md").exists()

            # Check package structure
            src_dir = output_dir / "src" / "test_cli"
            assert (src_dir / "__init__.py").exists()
            assert (src_dir / "cli.py").exists()
            assert (src_dir / "client.py").exists()
            assert (src_dir / "constants.py").exists()

            # Check commands
            commands_dir = src_dir / "commands"
            assert (commands_dir / "__init__.py").exists()
            assert (commands_dir / "users.py").exists()

    def test_generate_with_config(self):
        """Test generate with custom config."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[],
            )
        }

        config = self._default_config()
        config["DefaultBaseUrl"] = "https://api.example.com"
        config["Timeout"] = 60

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=config)
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            # Check constants has custom values
            constants_file = output_dir / "src" / "test_cli" / "constants.py"
            content = constants_file.read_text()
            assert "https://api.example.com" in content
            assert "60" in content

    def test_generate_multiple_groups(self):
        """Test generating multiple command groups."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[],
            ),
            "Orders": CommandGroup(
                name="Orders",
                cli_name="orders",
                description="Order management",
                operations=[],
            ),
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            commands_dir = output_dir / "src" / "test_cli" / "commands"
            assert (commands_dir / "users.py").exists()
            assert (commands_dir / "orders.py").exists()

    def test_generate_pyproject_content(self):
        """Test pyproject.toml content."""
        groups = {
            "Users": CommandGroup(
                name="Users", cli_name="users", description="", operations=[]
            )
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "my-cli"
            config = self._default_config(cli_name="my-cli", package_name="my_cli")
            generator = CliGenerator(config=config)
            generator.generate(groups, output_dir, "my-cli", "my_cli")

            pyproject = (output_dir / "pyproject.toml").read_text()
            # Template uses PackageName for project name
            assert 'name = "my_cli"' in pyproject
            assert 'my-cli = "my_cli.cli:main"' in pyproject

    def test_generate_readme_content(self):
        """Test README.md content."""
        groups = {
            "Users": CommandGroup(
                name="Users", cli_name="users", description="", operations=[]
            )
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "my-cli"
            config = self._default_config(cli_name="my-cli", package_name="my_cli")
            generator = CliGenerator(config=config)
            generator.generate(groups, output_dir, "my-cli", "my_cli")

            readme = (output_dir / "README.md").read_text()
            assert "my-cli" in readme
            assert "pip install" in readme

    def test_generate_command_with_parameters(self):
        """Test generating command with various parameters."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[
                    Operation(
                        operation_id="getUser",
                        method="GET",
                        path="/users/{userId}",
                        summary="Get user by ID",
                        description="",
                        tags=["Users"],
                        parameters=[
                            Parameter(
                                name="userId",
                                location="path",
                                param_type="string",
                                required=True,
                            ),
                            Parameter(
                                name="includeDetails",
                                location="query",
                                param_type="boolean",
                                required=False,
                            ),
                        ],
                    )
                ],
            )
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            users_file = output_dir / "src" / "test_cli" / "commands" / "users.py"
            content = users_file.read_text()
            assert "user_id" in content
            assert "include_details" in content

    def test_generate_command_with_body(self):
        """Test generating command with request body."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[
                    Operation(
                        operation_id="createUser",
                        method="POST",
                        path="/users",
                        summary="Create user",
                        description="",
                        tags=["Users"],
                        parameters=[],
                        body_properties=[
                            RequestBodyProperty(
                                name="name",
                                prop_type="string",
                                required=True,
                                description="User name",
                            ),
                            RequestBodyProperty(
                                name="email",
                                prop_type="string",
                                required=False,
                                description="User email",
                            ),
                        ],
                    )
                ],
            )
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            users_file = output_dir / "src" / "test_cli" / "commands" / "users.py"
            content = users_file.read_text()
            assert "--name" in content
            assert "--email" in content
            assert "required=True" in content

    def test_generate_copies_ca_and_splash_files(self):
        """Test that CA and splash files are copied into the resources directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()
            ca_file = config_dir / "ca.pem"
            ca_file.write_text("fake-ca-cert")
            splash_file = config_dir / "splash.txt"
            splash_file.write_text("fake-splash")

            config = self._default_config()
            config["CaFile"] = "ca.pem"
            config["SplashFile"] = "splash.txt"

            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=config, config_dir=config_dir)
            generator.generate({}, output_dir, "test-cli", "test_cli")

            resources_dir = output_dir / "src" / "test_cli" / "resources"
            assert (resources_dir / "ca.pem").read_text() == "fake-ca-cert"
            assert (resources_dir / "splash.txt").read_text() == "fake-splash"

    def test_generate_missing_ca_and_splash_files_skipped(self):
        """Test that missing CA/splash files are silently skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._default_config()
            config["CaFile"] = "missing-ca.pem"
            config["SplashFile"] = "missing-splash.txt"

            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=config, config_dir=Path(temp_dir))
            generator.generate({}, output_dir, "test-cli", "test_cli")

            resources_dir = output_dir / "src" / "test_cli" / "resources"
            assert list(resources_dir.iterdir()) == []

    def test_generate_with_github_workflows(self):
        """Test that .github files are generated when IncludeGithubWorkflows is set."""
        config = self._default_config()
        config["IncludeGithubWorkflows"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=config)
            generator.generate({}, output_dir, "test-cli", "test_cli")

            github_dir = output_dir / ".github"
            assert (github_dir / "CODEOWNERS").exists()
            assert (github_dir / "labels.yaml").exists()
            assert (github_dir / "ISSUE_TEMPLATE" / "bug-report.yml").exists()
            assert (github_dir / "workflows" / "test.yaml").exists()
            assert (github_dir / "dependabot.yaml").exists()

    def test_generated_pyproject_configures_ruff(self):
        """Test that the generated pyproject configures ruff and drops black."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate({}, output_dir, "test-cli", "test_cli")

            content = (output_dir / "pyproject.toml").read_text()

            assert "[tool.ruff]" in content
            assert "line-length = 88" in content
            assert 'target-version = "py312"' in content
            assert '["E", "F", "W", "I"]' in content

            assert "[tool.black]" not in content
            assert "black" not in content
            assert "flake8" not in content
            assert "autoflake" not in content

    def test_missing_ruff_is_fatal(self):
        """Test that a missing ruff aborts generation before writing anything."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())

            with patch(
                "cli_wizard.generator.generator.resolve_ruff",
                side_effect=RuffNotFoundError("ruff not found"),
            ):
                with pytest.raises(RuffNotFoundError):
                    generator.generate({}, output_dir, "test-cli", "test_cli")

            assert not output_dir.exists()

    def test_generated_workflow_uses_generated_package_name(self):
        """Test that the CI workflow references the generated package."""
        config = self._default_config()
        config["IncludeGithubWorkflows"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=config)
            generator.generate({}, output_dir, "test-cli", "test_cli")

            workflow = output_dir / ".github" / "workflows" / "test.yaml"
            content = workflow.read_text()

            assert "src/test_cli" in content
            assert "--cov=test_cli" in content
            assert "cli_wizard" not in content
            assert "flake8" not in content
            assert "black" not in content

            # GitHub Actions expressions collide with Jinja delimiters and
            # must survive rendering verbatim.
            assert "${{ matrix.python-version }}" in content
            assert "${{ secrets.CODECOV_TOKEN }}" in content

            # Rendering must not join lines or otherwise break the YAML.
            parsed = yaml.safe_load(content)
            steps = parsed["jobs"]["test"]["steps"]
            assert {"uses": "actions/checkout@v4"} in steps
            assert any(s.get("name") == "Lint with ruff" for s in steps)

    def _sample_groups(self) -> dict:
        """Create a sample command group for generation tests."""
        return {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="User management",
                operations=[
                    Operation(
                        operation_id="listUsers",
                        method="GET",
                        path="/users",
                        summary="List users",
                        description="",
                        tags=["Users"],
                        parameters=[],
                    )
                ],
            )
        }

    def test_generate_is_idempotent(self):
        """Test that generating twice produces byte-identical output."""
        groups = self._sample_groups()

        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first"
            second = Path(temp_dir) / "second"

            for target in (first, second):
                generator = CliGenerator(config=self._default_config())
                generator.generate(groups, target, "test-cli", "test_cli")

            first_files = sorted(
                p.relative_to(first) for p in first.rglob("*") if p.is_file()
            )
            second_files = sorted(
                p.relative_to(second) for p in second.rglob("*") if p.is_file()
            )

            assert first_files == second_files
            for rel in first_files:
                assert (first / rel).read_bytes() == (second / rel).read_bytes(), rel

            # Formatting must not leave a ruff cache behind in the output.
            assert not (first / ".ruff_cache").exists()

    def test_generated_output_is_ruff_clean(self):
        """Test that fresh output needs no further ruff changes."""
        groups = self._sample_groups()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate({}, output_dir, "test-cli", "test_cli")

            assert (output_dir / "pyproject.toml").exists()
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            ruff = resolve_ruff()
            for args in (("check",), ("format", "--check")):
                result = subprocess.run(
                    [*ruff, *args, str(output_dir)],
                    capture_output=True,
                )
                assert result.returncode == 0, result.stdout.decode()

    def test_format_recipe_matches_tox_template(self):
        """Test that the generator runs the same ruff commands as tox -e format."""
        from cli_wizard.generator import generator as generator_module

        template_path = (
            Path(generator_module.__file__).parents[1] / "templates" / "tox.ini.j2"
        )
        section = template_path.read_text().split("[testenv:format]")[1]
        section = section.split("[testenv:")[0]

        commands = []
        for line in section.splitlines():
            line = line.strip()
            if line.startswith("ruff "):
                tokens = line.split()[1:]
                commands.append(tuple(t for t in tokens if not t.endswith("/")))

        assert tuple(commands) == RUFF_COMMANDS

    def test_generated_code_uses_absolute_non_lazy_imports(self):
        """Test that generated code avoids relative and function-level imports."""
        groups = self._sample_groups()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            for py_file in sorted(output_dir.rglob("*.py")):
                tree = ast.parse(py_file.read_text())

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        assert node.level == 0, (
                            f"{py_file.name}:{node.lineno} uses a relative import"
                        )

                # Imports must live at module level, not inside functions.
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for inner in ast.walk(node):
                        assert not isinstance(inner, (ast.Import, ast.ImportFrom)), (
                            f"{py_file.name}:{getattr(inner, 'lineno', '?')} "
                            f"has a lazy import inside {node.name}"
                        )
