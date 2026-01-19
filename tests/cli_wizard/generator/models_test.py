# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for generator models."""

from cli_wizard.generator.models import (
    Parameter,
    RequestBodyProperty,
    Operation,
    CommandGroup,
)


class TestParameter:
    """Tests for Parameter model."""

    def test_cli_name_camel_case(self):
        """Test CLI name conversion from camelCase."""
        param = Parameter(
            name="userId", location="path", param_type="string", required=True
        )
        assert param.cli_name == "user-id"

    def test_cli_name_snake_case(self):
        """Test CLI name conversion from snake_case."""
        param = Parameter(
            name="user_id", location="path", param_type="string", required=True
        )
        assert param.cli_name == "user-id"

    def test_python_name_camel_case(self):
        """Test Python name conversion from camelCase."""
        param = Parameter(
            name="userId", location="path", param_type="string", required=True
        )
        assert param.python_name == "user_id"

    def test_python_name_kebab_case(self):
        """Test Python name conversion from kebab-case."""
        param = Parameter(
            name="user-id", location="path", param_type="string", required=True
        )
        assert param.python_name == "user_id"

    def test_click_type_string(self):
        """Test Click type for string."""
        param = Parameter(
            name="name", location="query", param_type="string", required=False
        )
        assert param.click_type == "str"

    def test_click_type_integer(self):
        """Test Click type for integer."""
        param = Parameter(
            name="limit", location="query", param_type="integer", required=False
        )
        assert param.click_type == "int"

    def test_click_type_number(self):
        """Test Click type for number."""
        param = Parameter(
            name="price", location="query", param_type="number", required=False
        )
        assert param.click_type == "float"

    def test_click_type_boolean(self):
        """Test Click type for boolean."""
        param = Parameter(
            name="active", location="query", param_type="boolean", required=False
        )
        assert param.click_type == "bool"

    def test_click_type_unknown(self):
        """Test Click type for unknown type defaults to str."""
        param = Parameter(
            name="data", location="query", param_type="object", required=False
        )
        assert param.click_type == "str"


class TestRequestBodyProperty:
    """Tests for RequestBodyProperty model."""

    def test_cli_name(self):
        """Test CLI name conversion."""
        prop = RequestBodyProperty(name="userName", prop_type="string", required=True)
        assert prop.cli_name == "user-name"

    def test_python_name(self):
        """Test Python name conversion."""
        prop = RequestBodyProperty(name="userName", prop_type="string", required=True)
        assert prop.python_name == "user_name"

    def test_click_type(self):
        """Test Click type conversion."""
        prop = RequestBodyProperty(name="count", prop_type="integer", required=True)
        assert prop.click_type == "int"


class TestOperation:
    """Tests for Operation model."""

    def test_command_name(self):
        """Test command name from operation ID."""
        op = Operation(
            operation_id="GetUserById",
            method="GET",
            path="/users/{id}",
            summary="Get user",
            description="",
            tags=["Users"],
            parameters=[],
        )
        assert op.command_name == "get-user-by-id"

    def test_function_name(self):
        """Test function name from operation ID."""
        op = Operation(
            operation_id="GetUserById",
            method="GET",
            path="/users/{id}",
            summary="Get user",
            description="",
            tags=["Users"],
            parameters=[],
        )
        assert op.function_name == "get_user_by_id"


class TestCommandGroup:
    """Tests for CommandGroup model."""

    def test_module_name(self):
        """Test module name from CLI name."""
        group = CommandGroup(
            name="API Keys",
            cli_name="api-keys",
            description="API key management",
        )
        assert group.module_name == "api_keys"
