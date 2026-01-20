# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for CLI generator."""

import tempfile
from pathlib import Path

from cli_wizard.generator.generator import CliGenerator, _build_url_path
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
            generator = CliGenerator()
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

        config = {
            "PackageName": "test-cli",
            "DefaultBaseUrl": "https://api.example.com",
            "Timeout": 60,
        }

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
            generator = CliGenerator()
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
            generator = CliGenerator()
            generator.generate(groups, output_dir, "my-cli", "my_cli")

            pyproject = (output_dir / "pyproject.toml").read_text()
            assert 'name = "my-cli"' in pyproject
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
            generator = CliGenerator()
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
            generator = CliGenerator()
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
            generator = CliGenerator()
            generator.generate(groups, output_dir, "test-cli", "test_cli")

            users_file = output_dir / "src" / "test_cli" / "commands" / "users.py"
            content = users_file.read_text()
            assert "--name" in content
            assert "--email" in content
            assert "required=True" in content
