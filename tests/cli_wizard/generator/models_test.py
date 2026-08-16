# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for generator models."""

import pytest

from cli_wizard.generator.models import (
    CommandGroup,
    Operation,
    Parameter,
    RequestBodyProperty,
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

    @pytest.mark.parametrize(
        ("items_type", "expected"),
        [("string", "str"), ("integer", "int"), (None, "str")],
    )
    def test_click_type_array_follows_items(self, items_type, expected):
        """Test Click type for an array comes from its item type."""
        param = Parameter(
            name="tags",
            location="query",
            param_type="array",
            required=False,
            items_type=items_type,
        )
        assert param.is_array
        assert param.click_type == expected

    @pytest.mark.parametrize("required", [True, False])
    def test_python_annotation_array_is_a_tuple(self, required):
        """Test an array parameter is annotated as a tuple, never optional."""
        param = Parameter(
            name="tags",
            location="query",
            param_type="array",
            required=required,
            items_type="string",
        )
        assert param.python_annotation == "tuple[str, ...]"

    def test_python_annotation_optional_scalar(self):
        """Test an optional scalar parameter is annotated as nullable."""
        param = Parameter(
            name="limit", location="query", param_type="integer", required=False
        )
        assert param.python_annotation == "int | None"


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

    def test_click_type_array_follows_items(self):
        """Test Click type for an array comes from its item type."""
        prop = RequestBodyProperty(
            name="ports", prop_type="array", required=True, items_type="integer"
        )
        assert prop.is_array
        assert prop.click_type == "int"

    def test_python_annotation_array_is_a_tuple(self):
        """Test an array property is annotated as a tuple."""
        prop = RequestBodyProperty(
            name="ports", prop_type="array", required=False, items_type="integer"
        )
        assert prop.python_annotation == "tuple[int, ...]"


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

    def test_path_parameters_keeps_only_path_ones_in_order(self):
        """Test path parameters are selected in declaration order."""
        op = Operation(
            operation_id="getOrderItem",
            method="GET",
            path="/orders/{orderId}/items/{itemId}",
            summary="Get order item",
            description="",
            tags=["Orders"],
            parameters=[
                Parameter(
                    name="orderId", location="path", param_type="string", required=True
                ),
                Parameter(
                    name="verbose",
                    location="query",
                    param_type="boolean",
                    required=False,
                ),
                Parameter(
                    name="itemId", location="path", param_type="string", required=True
                ),
                Parameter(
                    name="X-Trace",
                    location="header",
                    param_type="string",
                    required=False,
                ),
            ],
        )
        assert [p.name for p in op.path_parameters] == ["orderId", "itemId"]

    def test_query_parameters_keeps_only_query_ones(self):
        """Test query parameters exclude path and header parameters."""
        op = Operation(
            operation_id="listUsers",
            method="GET",
            path="/tenants/{tenantId}/users",
            summary="List users",
            description="",
            tags=["Users"],
            parameters=[
                Parameter(
                    name="tenantId", location="path", param_type="string", required=True
                ),
                Parameter(
                    name="limit", location="query", param_type="integer", required=False
                ),
                Parameter(
                    name="X-Trace",
                    location="header",
                    param_type="string",
                    required=False,
                ),
            ],
        )
        assert [p.name for p in op.query_parameters] == ["limit"]


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

    @pytest.mark.parametrize(
        "location,expected",
        [("path", True), ("query", False)],
    )
    def test_has_path_parameters(self, location, expected):
        """Test a group reports whether any operation takes a path parameter."""
        group = CommandGroup(
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
                ),
                Operation(
                    operation_id="getUser",
                    method="GET",
                    path="/users/{userId}",
                    summary="Get user",
                    description="",
                    tags=["Users"],
                    parameters=[
                        Parameter(
                            name="userId",
                            location=location,
                            param_type="string",
                            required=True,
                        )
                    ],
                ),
            ],
        )
        assert group.has_path_parameters is expected
