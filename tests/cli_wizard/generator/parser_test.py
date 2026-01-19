# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Tests for OpenAPI parser."""

import json
import tempfile
from pathlib import Path

import yaml

from cli_wizard.generator.parser import OpenApiParser


def create_temp_spec(content: dict, suffix: str = ".json") -> str:
    """Create a temporary OpenAPI spec file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        if suffix == ".json":
            json.dump(content, f)
        else:
            yaml.dump(content, f)
        return f.name


class TestOpenApiParser:
    """Tests for OpenApiParser."""

    def test_load_json_spec(self):
        """Test loading JSON OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        spec_path = create_temp_spec(spec, ".json")
        try:
            parser = OpenApiParser(spec_path)
            assert parser.spec["openapi"] == "3.0.0"
        finally:
            Path(spec_path).unlink()

    def test_load_yaml_spec(self):
        """Test loading YAML OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        spec_path = create_temp_spec(spec, ".yaml")
        try:
            parser = OpenApiParser(spec_path)
            assert parser.spec["openapi"] == "3.0.0"
        finally:
            Path(spec_path).unlink()

    def test_load_yml_spec(self):
        """Test loading .yml OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        spec_path = create_temp_spec(spec, ".yml")
        try:
            parser = OpenApiParser(spec_path)
            assert parser.spec["openapi"] == "3.0.0"
        finally:
            Path(spec_path).unlink()

    def test_parse_simple_get(self):
        """Test parsing a simple GET operation."""
        spec = {
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
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            assert "Users" in groups
            assert len(groups["Users"].operations) == 1
            assert groups["Users"].operations[0].operation_id == "listUsers"
            assert groups["Users"].operations[0].method == "GET"
        finally:
            Path(spec_path).unlink()

    def test_parse_with_path_parameter(self):
        """Test parsing operation with path parameter."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{userId}": {
                    "get": {
                        "operationId": "getUser",
                        "summary": "Get user",
                        "tags": ["Users"],
                        "parameters": [
                            {
                                "name": "userId",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert len(op.parameters) == 1
            assert op.parameters[0].name == "userId"
            assert op.parameters[0].location == "path"
            assert op.parameters[0].required is True
        finally:
            Path(spec_path).unlink()

    def test_parse_with_query_parameter(self):
        """Test parsing operation with query parameter."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "default": 10},
                                "description": "Max results",
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert op.parameters[0].name == "limit"
            assert op.parameters[0].location == "query"
            assert op.parameters[0].default == 10
        finally:
            Path(spec_path).unlink()

    def test_parse_exclude_tags(self):
        """Test excluding tags from parsing."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/health": {
                    "get": {
                        "operationId": "healthCheck",
                        "tags": ["Actuator"],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse(exclude_tags=["Actuator"])
            assert "Users" in groups
            assert "Actuator" not in groups
        finally:
            Path(spec_path).unlink()

    def test_parse_include_tags(self):
        """Test including only specific tags."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/orders": {
                    "get": {
                        "operationId": "listOrders",
                        "tags": ["Orders"],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse(include_tags=["Users"])
            assert "Users" in groups
            assert "Orders" not in groups
        finally:
            Path(spec_path).unlink()

    def test_parse_tag_mapping(self):
        """Test custom tag to CLI name mapping."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/keys": {
                    "get": {
                        "operationId": "listKeys",
                        "tags": ["API Keys"],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse(tag_mapping={"API Keys": "api-keys"})
            assert groups["API Keys"].cli_name == "api-keys"
        finally:
            Path(spec_path).unlink()

    def test_parse_request_body(self):
        """Test parsing request body properties."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "tags": ["Users"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["name"],
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "User name",
                                            },
                                            "email": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert len(op.body_properties) == 2
            name_prop = next(p for p in op.body_properties if p.name == "name")
            assert name_prop.required is True
            email_prop = next(p for p in op.body_properties if p.name == "email")
            assert email_prop.required is False
        finally:
            Path(spec_path).unlink()

    def test_parse_request_body_with_ref(self):
        """Test parsing request body with $ref."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "tags": ["Users"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/CreateUser"
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
            "components": {
                "schemas": {
                    "CreateUser": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert len(op.body_properties) == 1
            assert op.body_properties[0].name == "name"
        finally:
            Path(spec_path).unlink()

    def test_parse_tag_description(self):
        """Test getting tag description from spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "tags": [{"name": "Users", "description": "User management"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            assert groups["Users"].description == "User management"
        finally:
            Path(spec_path).unlink()

    def test_parse_default_tag(self):
        """Test operation without tags uses default."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "healthCheck",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            assert "default" in groups
        finally:
            Path(spec_path).unlink()

    def test_parse_all_http_methods(self):
        """Test parsing all HTTP methods."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/resource": {
                    "get": {
                        "operationId": "getResource",
                        "tags": ["Resource"],
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "operationId": "createResource",
                        "tags": ["Resource"],
                        "responses": {"201": {"description": "Created"}},
                    },
                    "put": {
                        "operationId": "updateResource",
                        "tags": ["Resource"],
                        "responses": {"200": {"description": "OK"}},
                    },
                    "patch": {
                        "operationId": "patchResource",
                        "tags": ["Resource"],
                        "responses": {"200": {"description": "OK"}},
                    },
                    "delete": {
                        "operationId": "deleteResource",
                        "tags": ["Resource"],
                        "responses": {"204": {"description": "Deleted"}},
                    },
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            methods = [op.method for op in groups["Resource"].operations]
            assert "GET" in methods
            assert "POST" in methods
            assert "PUT" in methods
            assert "PATCH" in methods
            assert "DELETE" in methods
        finally:
            Path(spec_path).unlink()

    def test_parse_enum_parameter(self):
        """Test parsing parameter with enum values."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "listUsers",
                        "tags": ["Users"],
                        "parameters": [
                            {
                                "name": "status",
                                "in": "query",
                                "schema": {
                                    "type": "string",
                                    "enum": ["active", "inactive", "pending"],
                                },
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            param = groups["Users"].operations[0].parameters[0]
            assert param.enum == ["active", "inactive", "pending"]
        finally:
            Path(spec_path).unlink()

    def test_load_unknown_extension_json(self):
        """Test loading file with unknown extension that contains JSON."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }
        spec_path = create_temp_spec(spec, ".txt")
        try:
            parser = OpenApiParser(spec_path)
            assert parser.spec["openapi"] == "3.0.0"
        finally:
            Path(spec_path).unlink()

    def test_load_unknown_extension_yaml(self):
        """Test loading file with unknown extension that contains YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'\npaths: {}\n"
            )
            spec_path = f.name
        try:
            parser = OpenApiParser(spec_path)
            assert parser.spec["openapi"] == "3.0.0"
        finally:
            Path(spec_path).unlink()

    def test_parse_invalid_ref(self):
        """Test parsing with invalid $ref."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "tags": ["Users"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/invalid/path"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert len(op.body_properties) == 0
        finally:
            Path(spec_path).unlink()

    def test_parse_missing_schema_ref(self):
        """Test parsing with $ref to non-existent schema."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "tags": ["Users"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/NonExistent"
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
            "components": {"schemas": {}},
        }
        spec_path = create_temp_spec(spec)
        try:
            parser = OpenApiParser(spec_path)
            groups = parser.parse()
            op = groups["Users"].operations[0]
            assert len(op.body_properties) == 0
        finally:
            Path(spec_path).unlink()
