# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for CLI generator."""

import ast
import configparser
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
import yaml
from click.testing import CliRunner

import cli_wizard
from cli_wizard.config.schema import (
    SUPPORTED_PYTHON_VERSIONS,
    Config,
    python_versions_from,
    ruff_target_version,
    tox_env_name,
)
from cli_wizard.generator.generator import (
    RUFF_COMMANDS,
    CliGenerator,
    RuffNotFoundError,
    _build_url_expression,
    _sensitive_field_names,
    resolve_ruff,
)
from cli_wizard.generator.models import (
    CommandGroup,
    Operation,
    Parameter,
    RequestBodyProperty,
)


@contextmanager
def _import_generated(output_dir: Path, package_name: str, module: str):
    """Import a module out of a freshly generated project."""
    src_dir = str(output_dir / "src")
    sys.path.insert(0, src_dir)
    try:
        yield importlib.import_module(f"{package_name}.{module}")
    finally:
        sys.path.remove(src_dir)
        for name in list(sys.modules):
            if name == package_name or name.startswith(f"{package_name}."):
                del sys.modules[name]


class TestBuildUrlExpression:
    """Tests for _build_url_expression helper."""

    def test_no_path_params(self):
        """Test a path without parameters stays a plain string literal."""
        op = Operation(
            operation_id="listUsers",
            method="GET",
            path="/users",
            summary="List users",
            description="",
            tags=["Users"],
            parameters=[],
        )
        assert _build_url_expression(op) == '"/users"'

    def test_single_path_param(self):
        """Test a single path parameter becomes an encoded f-string field."""
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
        assert _build_url_expression(op) == 'f"/users/{encode_path_param(user_id)}"'

    def test_multiple_path_params(self):
        """Test every path parameter is interpolated."""
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
        assert _build_url_expression(op) == (
            'f"/orders/{encode_path_param(order_id)}'
            '/items/{encode_path_param(item_id)}"'
        )

    def test_query_params_ignored(self):
        """Test that query parameters don't affect the URL expression."""
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
        assert _build_url_expression(op) == '"/users"'

    def test_undeclared_placeholder_stays_literal(self):
        """Test a placeholder with no matching parameter is escaped, not evaluated."""
        op = Operation(
            operation_id="getUser",
            method="GET",
            path="/users/{userId}/{unknown}",
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
        assert _build_url_expression(op) == (
            'f"/users/{encode_path_param(user_id)}/{{unknown}}"'
        )


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

    def test_generated_version_is_read_from_package_metadata(self):
        """Test the generated version comes from metadata, not a VERSION file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate({}, output_dir, "test-cli", "test_cli")

            content = (output_dir / "src" / "test_cli" / "constants.py").read_text()
            assert 'version("test_cli")' in content
            assert "VERSION" not in content

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

    def test_generated_command_reports_the_api_error_body(self):
        """Test that a rejected request surfaces the fields the API named."""
        response = requests.Response()
        response.status_code = 422
        response.reason = "Unprocessable Entity"
        response._content = json.dumps(
            {"detail": [{"loc": ["body", "name"], "msg": "Field required"}]}
        ).encode()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            groups = self._sample_groups()
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            with _import_generated(output_dir, "test_cli", "commands.users") as module:
                client = MagicMock()
                client.get.return_value = response
                with patch.object(module, "_get_client", return_value=client):
                    with patch.object(module, "load_profile"):
                        result = CliRunner().invoke(module.users, ["list-users"])

        assert result.exit_code == 1
        assert "Error: 422 Unprocessable Entity" in result.output
        assert "name: Field required" in result.output

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

    @pytest.mark.parametrize(
        "overrides, expected",
        [
            ({"CoverageThreshold": 95}, 95),
            # A config that never went through Config omits the key entirely.
            ({}, Config.get_field_default("CoverageThreshold")),
        ],
    )
    def test_generated_pyproject_gates_coverage(self, overrides, expected):
        """Test that the generated pyproject enforces the coverage threshold."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config={**self._default_config(), **overrides})
            generator.generate({}, output_dir, "test-cli", "test_cli")

            pyproject = tomllib.loads((output_dir / "pyproject.toml").read_text())
            assert pyproject["tool"]["coverage"]["report"]["fail_under"] == expected

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
            assert {"uses": "actions/checkout@v7"} in steps
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

    def test_generated_cli_shows_the_splash_from_the_callback(self):
        """Test that the splash screen is not an import-time side effect."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=self._default_config())
            generator.generate({}, output_dir, "test-cli", "test_cli")

            tree = ast.parse((output_dir / "src" / "test_cli" / "cli.py").read_text())
            main = next(
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main"
            )

            def calls(nodes):
                """Collect the calls made as statements in nodes."""
                return {
                    ast.unparse(node.value)
                    for node in nodes
                    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                }

            assert "_show_splash()" not in calls(tree.body)
            assert "_show_splash()" in calls(ast.walk(main))


class TestDebugOutputRedaction:
    """Debug output must never carry a credential to a bug report."""

    def _login_groups(self) -> dict:
        """Build a login operation with the credentials a spec can flag."""
        return {
            "Auth": CommandGroup(
                name="Auth",
                cli_name="auth",
                description="Authentication",
                operations=[
                    Operation(
                        operation_id="login",
                        method="POST",
                        path="/auth/login",
                        summary="Log in",
                        description="",
                        tags=["Auth"],
                        parameters=[
                            Parameter(
                                name="apiKey",
                                location="query",
                                param_type="string",
                                required=True,
                                spec_format="password",
                            )
                        ],
                        body_properties=[
                            RequestBodyProperty(
                                name="email", prop_type="string", required=True
                            ),
                            RequestBodyProperty(
                                name="passphrase",
                                prop_type="string",
                                required=True,
                                write_only=True,
                            ),
                        ],
                    )
                ],
            )
        }

    def test_sensitive_field_names_collects_flagged_fields(self):
        """Test format and writeOnly decide which names are collected."""
        assert _sensitive_field_names(self._login_groups()) == ["apiKey", "passphrase"]

    def test_sensitive_field_names_is_empty_without_flagged_fields(self):
        """Test a spec that flags nothing collects nothing."""
        groups = {
            "Users": CommandGroup(
                name="Users",
                cli_name="users",
                description="",
                operations=[
                    Operation(
                        operation_id="listUsers",
                        method="GET",
                        path="/users",
                        summary="",
                        description="",
                        tags=["Users"],
                        parameters=[],
                    )
                ],
            )
        }
        assert _sensitive_field_names(groups) == []

    def test_flagged_names_are_baked_into_the_redaction_module(self):
        """Test the generated module knows the names the spec flagged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=TestCliGenerator()._default_config())
            generator.generate(self._login_groups(), output_dir, "test-cli", "test_cli")

            content = (output_dir / "src" / "test_cli" / "redaction.py").read_text()
            assert '"apiKey"' in content
            assert '"passphrase"' in content

    def test_no_template_logs_a_raw_payload(self):
        """Test every payload the generated code logs goes through redaction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=TestCliGenerator()._default_config())
            generator.generate(self._login_groups(), output_dir, "test-cli", "test_cli")

            src_dir = output_dir / "src" / "test_cli"
            leaks = (
                "{cmd_params}",
                "{output[",
                "{json_data}",
                "{params}",
                "{response.text[",
                "{dict(self.session.headers)}",
                "{dict(response.headers)}",
            )
            for py_file in (src_dir / "client.py", src_dir / "commands" / "auth.py"):
                content = py_file.read_text()
                for leak in leaks:
                    assert leak not in content, f"{py_file.name} logs {leak} unredacted"


def _parse_pyproject_pins(text):
    """Collect ``name -> specifier`` from every dependency array in a pyproject."""
    pins = {}
    pattern = r"^(?:dependencies|test|dev|docs) = \[(.*?)^]"
    for block in re.findall(pattern, text, re.S | re.M):
        # Drop {include-group = "..."} entries: they name a group, not a package.
        block = re.sub(r"\{include-group = \"[^\"]+\"\},?", "", block)
        for entry in re.findall(r'"([^"]+)"', block):
            name, specifier = re.match(r"([A-Za-z0-9_.-]+)(.*)", entry).groups()
            pins[name.lower()] = specifier
    return pins


TEMPLATES_DIR = Path(cli_wizard.__file__).parent / "templates"
REPO_ROOT = Path(__file__).parents[3]


class TestDependencyPins:
    """Common dependencies must be pinned identically everywhere they appear."""

    def test_cli_wizard_and_generated_pyproject_agree(self):
        """Test that shared deps use the same specifier in both pyprojects."""
        ours = _parse_pyproject_pins((REPO_ROOT / "pyproject.toml").read_text())
        theirs = _parse_pyproject_pins(
            (TEMPLATES_DIR / "pyproject.toml.j2").read_text()
        )

        shared = sorted(set(ours) & set(theirs))
        assert shared, "expected the two pyprojects to share dependencies"

        mismatched = {n: (ours[n], theirs[n]) for n in shared if ours[n] != theirs[n]}
        assert not mismatched, f"pins differ between pyprojects: {mismatched}"

    @pytest.mark.parametrize(
        "tox_path",
        [REPO_ROOT / "tox.ini", TEMPLATES_DIR / "tox.ini.j2"],
        ids=["cli-wizard", "generated"],
    )
    def test_tox_declares_no_dependencies_of_its_own(self, tox_path):
        """Test that tox reads its versions from pyproject instead of repeating them."""
        text = tox_path.read_text()

        declared = [
            line for line in text.splitlines() if line.strip().startswith("deps =")
        ]
        assert not declared, (
            f"{tox_path.name} declares dependencies pyproject.toml already pins: "
            f"{declared}"
        )
        assert "dependency_groups =" in text, (
            f"{tox_path.name} declares no dependency groups"
        )


# Distributions whose import name differs from the name on the index.
IMPORT_NAMES = {"pyyaml": "yaml"}


class TestPublishedDependenciesAreUsed:
    """A generated CLI must not publish libraries it never imports."""

    def test_every_runtime_dependency_is_imported(self, tmp_path):
        """Test that each published dependency is imported by the generated code."""
        output_dir = tmp_path / "test-cli"
        generator = CliGenerator(config=Config(ProjectName="Test Cli").model_dump())
        generator.generate({}, output_dir, "test-cli", "test_cli")

        imported = set()
        for py_file in output_dir.rglob("*.py"):
            for node in ast.walk(ast.parse(py_file.read_text())):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])

        pyproject = tomllib.loads((output_dir / "pyproject.toml").read_text())
        declared = {
            re.match(r"[A-Za-z0-9_.-]+", dep).group().lower()
            for dep in pyproject["project"]["dependencies"]
        }

        unused = {d for d in declared if IMPORT_NAMES.get(d, d) not in imported}
        assert not unused, f"declared but never imported: {sorted(unused)}"


# Tooling nobody installing from an index should be offered. cli-wizard also
# publishes to PyPI (twine), builds docs (sphinx) and bundles ruff as a runtime
# dependency, so the two lists are not the same.
CLI_WIZARD_TOOLING = ("build", "mypy", "pre-commit", "pytest", "tox", "twine", "sphinx")
GENERATED_TOOLING = ("build", "mypy", "pre-commit", "pytest", "ruff", "tox")


class TestDevToolingIsNotPublished:
    """Dev tooling belongs in a PEP 735 group, and nothing local-only is published."""

    @staticmethod
    def _generated_pyproject(temp_dir):
        """Render a project and return its parsed pyproject.toml."""
        output_dir = Path(temp_dir) / "test-cli"
        generator = CliGenerator(
            config={
                "CommandName": "test-cli",
                "PackageName": "test_cli",
                "Description": "A test CLI",
                "PythonVersion": "3.12",
                "RepositoryUrl": "https://github.com/test/test-cli",
            }
        )
        generator.generate({}, output_dir, "test-cli", "test_cli")
        return tomllib.loads((output_dir / "pyproject.toml").read_text())

    @staticmethod
    def _flatten(groups):
        """Flatten a [dependency-groups] table, dropping include-group markers."""
        return " ".join(
            dep for deps in groups.values() for dep in deps if isinstance(dep, str)
        )

    def test_generated_project_publishes_no_extras(self):
        """Test that a generated CLI ships no optional dependencies at all."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject = self._generated_pyproject(temp_dir)

        assert "optional-dependencies" not in pyproject["project"]

    def test_generated_project_keeps_its_toolchain_in_a_group(self):
        """Test that a generated CLI's toolchain is local-only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject = self._generated_pyproject(temp_dir)

        groups = self._flatten(pyproject["dependency-groups"])
        published = " ".join(pyproject["project"]["dependencies"])
        for tool in GENERATED_TOOLING:
            assert tool in groups, f"{tool} missing from the dependency groups"
            assert tool not in published, f"{tool} is published"

    @pytest.mark.parametrize(
        ("pyproject_path", "expected"),
        [
            (REPO_ROOT / "pyproject.toml", ["dev", "test", "docs"]),
            (None, ["dev", "test", "docs"]),
        ],
        ids=["cli-wizard", "generated"],
    )
    def test_groups_are_declared_in_order(self, pyproject_path, expected, tmp_path):
        """Test that dependency groups keep the declared order, widest first."""
        if pyproject_path is None:
            pyproject = self._generated_pyproject(tmp_path)
        else:
            pyproject = tomllib.loads(pyproject_path.read_text())

        assert list(pyproject["dependency-groups"]) == expected

    @pytest.mark.parametrize(
        "pyproject_path",
        [REPO_ROOT / "pyproject.toml", None],
        ids=["cli-wizard", "generated"],
    )
    def test_dev_group_includes_every_other_group(self, pyproject_path, tmp_path):
        """Test that `--group dev` is enough to get the whole toolchain."""
        if pyproject_path is None:
            pyproject = self._generated_pyproject(tmp_path)
        else:
            pyproject = tomllib.loads(pyproject_path.read_text())

        groups = pyproject["dependency-groups"]
        included = {
            dep["include-group"] for dep in groups["dev"] if isinstance(dep, dict)
        }
        assert included == set(groups) - {"dev"}

    def test_generated_project_urls_follow_the_config(self):
        """Test that Homepage takes HomePageUrl and Repository takes RepositoryUrl."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(
                config=Config(
                    ProjectName="Test Cli",
                    RepositoryUrl="https://github.com/test/test-cli",
                    HomePageUrl="https://test.github.io/test-cli/",
                ).model_dump()
            )
            generator.generate({}, output_dir, "test-cli", "test_cli")
            urls = tomllib.loads((output_dir / "pyproject.toml").read_text())
            urls = urls["project"]["urls"]

        assert urls["Homepage"] == "https://test.github.io/test-cli/"
        assert urls["Repository"] == "https://github.com/test/test-cli"

    def test_generated_home_page_falls_back_to_the_repository(self):
        """Test that a project not setting HomePageUrl still gets a usable one."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(
                config=Config(
                    ProjectName="Test Cli",
                    RepositoryUrl="https://github.com/test/test-cli",
                ).model_dump()
            )
            generator.generate({}, output_dir, "test-cli", "test_cli")
            urls = tomllib.loads((output_dir / "pyproject.toml").read_text())
            urls = urls["project"]["urls"]

        assert urls["Homepage"] == urls["Repository"]

    def test_generated_dev_group_includes_the_test_group(self):
        """Test that one ``--group dev`` install is enough to run the suite."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pyproject = self._generated_pyproject(temp_dir)

        groups = pyproject["dependency-groups"]
        assert {"include-group": "test"} in groups["dev"]
        assert any("pytest" in dep for dep in groups["test"])

    def test_cli_wizard_keeps_its_own_toolchain_in_a_group(self):
        """Test that cli-wizard applies to itself what it generates."""
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

        assert "optional-dependencies" not in pyproject["project"]
        assert {"include-group": "test"} in pyproject["dependency-groups"]["dev"]

        groups = self._flatten(pyproject["dependency-groups"])
        published = " ".join(pyproject["project"]["dependencies"])
        for tool in CLI_WIZARD_TOOLING:
            assert tool in groups, f"{tool} missing from the dependency groups"
            assert tool not in published, f"{tool} is published"

    @pytest.mark.parametrize(
        "recipe_paths",
        [
            (
                REPO_ROOT / "Makefile",
                REPO_ROOT / ".github" / "workflows" / "test.yaml",
                REPO_ROOT / ".github" / "workflows" / "pr-validation.yaml",
            ),
            (
                "Makefile",
                ".github/workflows/test.yaml",
                ".github/workflows/pr-validation.yaml",
            ),
        ],
        ids=["cli-wizard", "generated"],
    )
    def test_every_install_recipe_is_the_same_command(self, recipe_paths, tmp_path):
        """Test that one command installs the toolchain, wherever it is installed."""
        if not isinstance(recipe_paths[0], Path):
            output_dir = tmp_path / "test-cli"
            generator = CliGenerator(
                config={
                    "CommandName": "test-cli",
                    "PackageName": "test_cli",
                    "PythonVersion": "3.12",
                    "IncludeGithubWorkflows": True,
                }
            )
            generator.generate({}, output_dir, "test-cli", "test_cli")
            recipe_paths = [output_dir / rel for rel in recipe_paths]

        # Every line that installs the dev toolchain. `--group docs` is a
        # different job and is deliberately not compared against these.
        found = set()
        for path in recipe_paths:
            for line in path.read_text().splitlines():
                line = line.strip()
                if "--group dev" in line:
                    found.add(line)

        assert found, f"no toolchain install found in {recipe_paths}"
        assert found == {"pip install -e . --group dev"}, (
            f"install recipes disagree: {sorted(found)}"
        )

    @pytest.mark.parametrize(
        "root",
        [REPO_ROOT, None],
        ids=["cli-wizard", "generated"],
    )
    def test_no_file_installs_an_extra(self, root, tmp_path):
        """Test that nothing reaches for an extra the project no longer declares.

        This sweeps every file rather than a list of the recipes we remember,
        because the generated docs workflow was missed exactly that way.
        """
        if root is None:
            root = tmp_path / "test-cli"
            generator = CliGenerator(
                config=Config(
                    ProjectName="Test Cli", IncludeGithubWorkflows=True
                ).model_dump()
            )
            generator.generate({}, root, "test-cli", "test_cli")
            paths = [p for p in root.rglob("*") if p.is_file()]
        else:
            workflows = (root / ".github" / "workflows").glob("*.yaml")
            paths = [root / "Makefile", *workflows]

        offenders = [
            path.name
            for path in paths
            if re.search(r"pip install [^\n]*-e [\"']?\.[\"']?\[", path.read_text())
        ]
        assert not offenders, f"these install an extra: {offenders}"


class TestGeneratedToxContract:
    """Whatever a generated project tells you to run has to exist and be correct."""

    @staticmethod
    def _generate(temp_dir):
        """Render a project with its workflows and return the output directory."""
        output_dir = Path(temp_dir) / "test-cli"
        generator = CliGenerator(
            config=Config(
                ProjectName="Test Cli", IncludeGithubWorkflows=True
            ).model_dump()
        )
        generator.generate({}, output_dir, "test-cli", "test_cli")
        return output_dir

    def test_every_tox_env_referenced_elsewhere_exists(self, tmp_path):
        """Test that no recipe or doc points at a tox env the project lacks."""
        output_dir = self._generate(tmp_path)

        tox_ini = (output_dir / "tox.ini").read_text()
        defined = set(re.findall(r"^\[testenv:([\w-]+)]", tox_ini, re.M))
        defined.update(re.findall(r"\bpy\d+\b", tox_ini))

        referenced = {}
        sources = [
            output_dir / "DEVELOPMENT.md",
            output_dir / ".github" / "workflows" / "test.yaml",
            output_dir / ".github" / "workflows" / "pr-validation.yaml",
        ]
        for source in sources:
            for envs in re.findall(r"tox (?:-r )?-e ([\w,.-]+)", source.read_text()):
                for env in envs.split(","):
                    referenced.setdefault(env, source.name)

        missing = {env: src for env, src in referenced.items() if env not in defined}
        assert not missing, f"tox envs referenced but not defined: {missing}"

    def test_coverage_gate_measures_the_generated_package(self, tmp_path):
        """Test that no recipe measures coverage of cli-wizard's own package."""
        output_dir = self._generate(tmp_path)

        measured = set()
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                measured.update(re.findall(r"--cov=([\w.]+)", path.read_text()))

        assert measured == {"test_cli"}, f"unexpected coverage targets: {measured}"


class TestGeneratedToxEnvlist:
    """A bare ``tox`` must lint and type check, not just run the tests."""

    def test_default_environments_run_ruff_and_mypy(self):
        """Test that the linters are in the envlist, not merely declared.

        Asserting on the commands rather than on environment names: ruff and
        mypy have already moved between environments once.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            generator = CliGenerator(config=Config(ProjectName="Test Cli").model_dump())
            generator.generate({}, output_dir, "test-cli", "test_cli")
            tox = configparser.ConfigParser()
            tox.read_string((output_dir / "tox.ini").read_text(encoding="utf-8"))

        commands = "".join(
            tox[section].get("commands", "")
            for env in tox["tox"]["envlist"].split(",")
            if tox.has_section(section := f"testenv:{env.strip()}")
        )

        assert "ruff check" in commands, commands
        assert "ruff format --check" in commands, commands
        assert "mypy" in commands, commands


class TestGeneratedPythonVersions:
    """A generated project's version matrix must follow its PythonVersion."""

    @staticmethod
    def _generate(python_version, temp_dir):
        config = Config(
            ProjectName="Test Cli",
            PythonVersion=python_version,
            IncludeGithubWorkflows=True,
        )
        output_dir = Path(temp_dir) / "test-cli"
        generator = CliGenerator(config=config.model_dump())
        generator.generate({}, output_dir, "test-cli", "test_cli")
        return output_dir

    @pytest.mark.parametrize("minimum", SUPPORTED_PYTHON_VERSIONS)
    def test_declarations_agree_with_python_version(self, minimum):
        """Test that every version declaration follows the configured minimum."""
        expected = python_versions_from(minimum)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = self._generate(minimum, temp_dir)

            pyproject = tomllib.loads(
                (output_dir / "pyproject.toml").read_text(encoding="utf-8")
            )
            assert pyproject["project"]["requires-python"] == f">={minimum}"
            assert [
                c.rsplit(" :: ", 1)[1]
                for c in pyproject["project"]["classifiers"]
                if c.startswith("Programming Language :: Python :: 3.")
            ] == expected
            # Ruff must target the minimum: it emits syntax valid for the
            # target, and PEP 758 syntax at py314 is a SyntaxError on 3.12.
            assert pyproject["tool"]["ruff"]["target-version"] == (
                ruff_target_version(minimum)
            )
            assert pyproject["tool"]["mypy"]["python_version"] == minimum

            tox_ini = (output_dir / "tox.ini").read_text(encoding="utf-8")
            envlist = re.search(r"^envlist = (.+)$", tox_ini, re.M).group(1)
            envs = [e.strip() for e in envlist.split(",")]
            assert [e for e in envs if e.startswith("py3")] == [
                tox_env_name(v) for v in expected
            ]

            workflow = yaml.safe_load(
                (output_dir / ".github" / "workflows" / "test.yaml").read_text(
                    encoding="utf-8"
                )
            )
            matrix = workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
            assert [str(v) for v in matrix] == expected

    @pytest.mark.parametrize("minimum", SUPPORTED_PYTHON_VERSIONS)
    def test_generated_sources_parse_on_the_declared_minimum(self, minimum):
        """Test that no template emits syntax newer than the configured minimum.

        The templates are shared across every PythonVersion, and ruff formats
        the output for the target version, so a construct such as PEP 758's
        unparenthesized ``except A, B:`` would parse for the generator and be
        a SyntaxError in the generated project.
        """
        feature_version = tuple(int(part) for part in minimum.split("."))
        if sys.version_info[:2] < feature_version:
            pytest.skip(f"parsing {minimum} syntax needs a {minimum} interpreter")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = self._generate(minimum, temp_dir)

            sources = sorted(output_dir.rglob("*.py"))
            assert sources, "expected the generator to write Python sources"
            for path in sources:
                ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                    feature_version=feature_version,
                )

    def test_single_version_workflows_use_the_declared_minimum(self):
        """Test that docs, release and pr-validation pin the project's minimum.

        These were static files hardcoding 3.12, so a project with a higher
        minimum got CI whose pip install failed against its own
        requires-python.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = self._generate("3.13", temp_dir)
            workflows = output_dir / ".github" / "workflows"

            docs = yaml.safe_load((workflows / "docs.yaml").read_text())
            assert docs["jobs"]["build"]["steps"][1]["with"]["python-version"] == "3.13"

            release = yaml.safe_load((workflows / "release.yaml").read_text())
            steps = release["jobs"]["publish"]["steps"]
            setup = next(s for s in steps if "setup-python" in s.get("uses", ""))
            assert setup["with"]["python-version"] == "3.13"

            validation = yaml.safe_load((workflows / "pr-validation.yaml").read_text())
            matrix = validation["jobs"]["validate"]["strategy"]["matrix"]
            assert [str(v) for v in matrix["python-version"]] == ["3.13"]

    def test_no_superseded_version_leaks_into_the_project(self):
        """Test that raising the minimum removes the older version everywhere."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = self._generate("3.13", temp_dir)

            offenders = []
            for path in sorted(output_dir.rglob("*")):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if "3.12" in text or "py312" in text:
                    offenders.append(str(path.relative_to(output_dir)))

            assert not offenders, f"3.12 leaked into a 3.13 project: {offenders}"

    def test_github_expressions_survive_rendering_in_all_workflows(self):
        """Test that ${{ }} expressions are not eaten by Jinja in any workflow.

        docs, release and pr-validation became templates, so their GitHub
        expressions now pass through the same delimiter collision that
        test.yaml already had to escape.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = self._generate("3.12", temp_dir)
            workflows = output_dir / ".github" / "workflows"

            expected = {
                "docs.yaml": "${{ steps.deployment.outputs.page_url }}",
                "release.yaml": "${{ secrets.PYPI_API_TOKEN }}",
                "pr-validation.yaml": "${{ matrix.python-version }}",
            }
            for name, expression in expected.items():
                content = (workflows / name).read_text(encoding="utf-8")
                assert expression in content, f"{name} lost {expression}"
                assert "{{" not in content.replace("${{", ""), (
                    f"{name} has an unrendered Jinja delimiter"
                )


class TestGeneratedPathExpansion:
    """Regression tests for #43: generated paths must not depend on $HOME."""

    @pytest.mark.parametrize(
        "constant,param",
        [
            ("MAIN_DIR", "MainDir"),
            ("PROFILE_FILE", "ProfileFile"),
            ("LOG_FILE", "LogFile"),
        ],
    )
    def test_home_resolves_without_the_home_variable(self, constant, param):
        """Test a ${HOME} path resolves under the home directory when HOME is unset."""
        config = {
            "CommandName": "test-cli",
            "PackageName": "test_cli",
            "Description": "A test CLI",
            "AuthorName": "Test Author",
            "AuthorEmail": "test@example.com",
            "PythonVersion": "3.12",
            "RepositoryUrl": "https://github.com/test/test-cli",
            param: "${HOME}/.test-cli",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test-cli"
            CliGenerator(config=config).generate({}, output_dir, "test-cli", "test_cli")

            spec = importlib.util.spec_from_file_location(
                "generated_constants", output_dir / "src" / "test_cli" / "constants.py"
            )
            module = importlib.util.module_from_spec(spec)
            with patch.dict(os.environ, {}, clear=True):
                spec.loader.exec_module(module)

            assert getattr(module, constant) == Path.home() / ".test-cli"


ISSUE23_PACKAGE = "issue23_cli"
ISSUE23_BASE_URL = "http://api.test"


def _issue23_groups():
    """Build a group whose operations cover path, query and body inputs."""
    email = Parameter(name="email", location="path", param_type="string", required=True)
    return {
        "Ops": CommandGroup(
            name="Ops",
            cli_name="ops",
            description="Operations",
            operations=[
                Operation(
                    operation_id="getUser",
                    method="GET",
                    path="/users/{userId}",
                    summary="Get user",
                    description="",
                    tags=["Ops"],
                    parameters=[
                        Parameter(
                            name="userId",
                            location="path",
                            param_type="string",
                            required=True,
                        ),
                        Parameter(
                            name="limit",
                            location="query",
                            param_type="integer",
                            required=False,
                        ),
                    ],
                ),
                Operation(
                    operation_id="updateBetaAccess",
                    method="PATCH",
                    path="/admin/beta-access/{email}",
                    summary="Update beta access",
                    description="",
                    tags=["Ops"],
                    parameters=[email],
                    body_properties=[
                        RequestBodyProperty(
                            name="enabled", prop_type="boolean", required=False
                        )
                    ],
                ),
                Operation(
                    operation_id="revokeBetaAccess",
                    method="DELETE",
                    path="/admin/beta-access/{email}",
                    summary="Revoke beta access",
                    description="",
                    tags=["Ops"],
                    parameters=[
                        email,
                        Parameter(
                            name="reason",
                            location="query",
                            param_type="string",
                            required=False,
                        ),
                    ],
                ),
            ],
        )
    }


@pytest.fixture(scope="module")
def issue23_cli(tmp_path_factory):
    """Generate a CLI with path parameters and import its entry point."""
    output_dir = tmp_path_factory.mktemp("issue23") / "cli"
    config = {
        "CommandName": "issue23-cli",
        "PackageName": ISSUE23_PACKAGE,
        "Description": "A test CLI",
        "AuthorName": "Test Author",
        "AuthorEmail": "test@example.com",
        "PythonVersion": "3.12",
        "DefaultBaseUrl": ISSUE23_BASE_URL,
        "RepositoryUrl": "https://github.com/test/issue23-cli",
        # Keep the profile file the commands write out of the real home.
        "MainDir": str(output_dir / "home"),
    }
    generator = CliGenerator(config=config)
    generator.generate(_issue23_groups(), output_dir, "issue23-cli", ISSUE23_PACKAGE)

    src_dir = str(output_dir / "src")
    sys.path.insert(0, src_dir)
    try:
        yield importlib.import_module(f"{ISSUE23_PACKAGE}.cli").main
    finally:
        sys.path.remove(src_dir)
        for name in list(sys.modules):
            if name == ISSUE23_PACKAGE or name.startswith(f"{ISSUE23_PACKAGE}."):
                del sys.modules[name]


def _invoke_issue23(cli, args):
    """Run a generated command against a mocked transport."""
    with patch("requests.Session.request") as request:
        request.return_value.text = ""
        result = CliRunner().invoke(cli, [*args, "--base-url", ISSUE23_BASE_URL])
    assert result.exit_code == 0, result.output
    return request.call_args


class TestGeneratedPathParameters:
    """Regression tests for #23: path parameters must reach the request URL."""

    def test_path_parameter_is_substituted_into_the_url(self, issue23_cli):
        """Test a path parameter value replaces its placeholder."""
        call = _invoke_issue23(issue23_cli, ["ops", "get-user", "--user-id", "42"])
        assert call.args == ("GET", f"{ISSUE23_BASE_URL}/users/42")

    @pytest.mark.parametrize(
        "value,encoded",
        [
            ("a@b.com", "a%40b.com"),
            ("with space", "with%20space"),
            ("with/slash", "with%2Fslash"),
            ("100%", "100%25"),
        ],
    )
    def test_path_parameter_is_percent_encoded(self, issue23_cli, value, encoded):
        """Test a path parameter value cannot alter the URL structure."""
        call = _invoke_issue23(issue23_cli, ["ops", "get-user", "--user-id", value])
        assert call.args == ("GET", f"{ISSUE23_BASE_URL}/users/{encoded}")

    def test_path_parameter_is_substituted_alongside_a_body(self, issue23_cli):
        """Test a path parameter reaches the URL of a request that has a body."""
        call = _invoke_issue23(
            issue23_cli,
            ["ops", "update-beta-access", "--email", "a@b.com", "--enabled"],
        )
        assert call.args == (
            "PATCH",
            f"{ISSUE23_BASE_URL}/admin/beta-access/a%40b.com",
        )
        assert call.kwargs["json"] == {"enabled": True}

    def test_query_parameters_are_sent_on_a_get_request(self, issue23_cli):
        """Test query parameters reach a GET request that also has a path one."""
        call = _invoke_issue23(
            issue23_cli, ["ops", "get-user", "--user-id", "42", "--limit", "5"]
        )
        assert call.kwargs["params"] == {"limit": 5}

    def test_query_parameters_are_sent_on_a_non_get_request(self, issue23_cli):
        """Test query parameters reach a DELETE request."""
        call = _invoke_issue23(
            issue23_cli,
            ["ops", "revoke-beta-access", "--email", "a@b.com", "--reason", "spam"],
        )
        assert call.kwargs["params"] == {"reason": "spam"}


class TestGeneratedGlobalOptions:
    """Regression tests for #27: root options must reach the subcommands."""

    def _invoke(self, cli, root_args, command_args):
        """Run a generated command with the transport and its effects mocked."""
        args = [*root_args, "ops", "get-user", "--user-id", "42", *command_args]
        with (
            patch("requests.Session.request") as request,
            patch(f"{ISSUE23_PACKAGE}.commands.ops.load_profile") as load_profile,
            patch(f"{ISSUE23_PACKAGE}.commands.ops.set_debug") as set_debug,
        ):
            request.return_value.text = ""
            result = CliRunner().invoke(cli, args)
        assert result.exit_code == 0, result.output
        return request, load_profile, set_debug

    @pytest.mark.parametrize(
        "root_args,command_args,expected",
        [
            (["--base-url", "http://root"], [], "http://root"),
            ([], ["--base-url", "http://leaf"], "http://leaf"),
            (
                ["--base-url", "http://root"],
                ["--base-url", "http://leaf"],
                "http://leaf",
            ),
            ([], [], ISSUE23_BASE_URL),
        ],
    )
    def test_base_url_precedence(self, issue23_cli, root_args, command_args, expected):
        """Test the command uses the root base URL unless it is given its own."""
        request, _, _ = self._invoke(issue23_cli, root_args, command_args)
        assert request.call_args.args[1] == f"{expected}/users/42"

    @pytest.mark.parametrize(
        "root_args,command_args,expected",
        [
            (["--profile", "root"], [], "root"),
            ([], ["--profile", "leaf"], "leaf"),
            (["--profile", "root"], ["--profile", "leaf"], "leaf"),
            ([], [], "default"),
        ],
    )
    def test_profile_precedence(self, issue23_cli, root_args, command_args, expected):
        """Test the command loads the root profile unless it is given its own."""
        _, load_profile, _ = self._invoke(issue23_cli, root_args, command_args)
        assert load_profile.call_args.args[0] == expected

    def test_root_debug_survives_the_group(self, issue23_cli):
        """Test a root --debug is not undone by the group or the command."""
        _, _, set_debug = self._invoke(issue23_cli, ["--debug"], [])
        assert set_debug.call_args.args[0] is True


def _issue50_groups():
    """Extend the #23 group with the option kinds it does not cover."""
    groups = _issue23_groups()
    groups["Ops"].operations.append(
        Operation(
            operation_id="createReport",
            method="POST",
            path="/reports",
            summary="Create report",
            description="",
            tags=["Ops"],
            parameters=[
                Parameter(
                    name="format",
                    location="query",
                    param_type="string",
                    required=True,
                    enum=["json", "csv"],
                )
            ],
            body_properties=[
                RequestBodyProperty(name="title", prop_type="string", required=True),
                RequestBodyProperty(name="ratio", prop_type="number", required=False),
            ],
        )
    )
    return groups


@pytest.fixture(scope="module")
def issue50_cli(tmp_path_factory):
    """Generate a CLI whose commands cover every kind of option."""
    output_dir = tmp_path_factory.mktemp("issue50") / "cli"
    config = {
        "CommandName": "issue50-cli",
        "PackageName": "issue50_cli",
        "Description": "A test CLI",
        "AuthorName": "Test Author",
        "AuthorEmail": "test@example.com",
        "PythonVersion": "3.12",
        "DefaultBaseUrl": ISSUE23_BASE_URL,
        "RepositoryUrl": "https://github.com/test/issue50-cli",
        # Keep the profile file the commands write out of the real home.
        "MainDir": str(output_dir / "home"),
    }
    generator = CliGenerator(config=config)
    generator.generate(_issue50_groups(), output_dir, "issue50-cli", "issue50_cli")
    return output_dir


class TestGeneratedCommandTests:
    """Regression tests for #50: the generated suite must run the commands."""

    def test_every_operation_gets_a_test(self, issue50_cli):
        """Test each spec-derived command is exercised by its own test."""
        content = (issue50_cli / "tests" / "commands_test.py").read_text()
        for op in _issue50_groups()["Ops"].operations:
            assert f"def test_{op.function_name}(" in content

    def test_generated_command_tests_pass(self, issue50_cli):
        """Test the generated command tests hold against the generated code."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/commands_test.py", "-q"],
            cwd=issue50_cli,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout.decode()

    @pytest.mark.parametrize(
        "command,method,path,params,body",
        [
            ("get_user", "GET", "/users/a%40b.com", {"limit": 1}, None),
            (
                "update_beta_access",
                "PATCH",
                "/admin/beta-access/a%40b.com",
                None,
                {"enabled": True},
            ),
            (
                "revoke_beta_access",
                "DELETE",
                "/admin/beta-access/a%40b.com",
                {"reason": "test"},
                None,
            ),
            (
                "create_report",
                "POST",
                "/reports",
                {"format": "json"},
                {"title": "test", "ratio": 1.5},
            ),
        ],
    )
    def test_expected_request_is_asserted(
        self, issue50_cli, command, method, path, params, body
    ):
        """Test the generated test states the URL, the verb and the JSON types."""
        content = (issue50_cli / "tests" / "commands_test.py").read_text()
        test = content.split(f"def test_{command}(")[1].split("    def ")[0]
        asserted = {
            match.group(1): ast.literal_eval(match.group(2))
            for match in re.finditer(r'kwargs\["(\w+)"\] (?:==|is) (.+)', test)
        }

        assert f'("{method}", BASE_URL + "{path}")' in test
        assert asserted["params"] == params
        if method == "GET":
            assert "json" not in asserted  # a GET carries no body
        else:
            assert asserted["json"] == body
