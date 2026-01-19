# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""OpenAPI specification parser."""

import json
from pathlib import Path
from typing import Any

import yaml

from cli_wizard.generator.models import (
    CommandGroup,
    Operation,
    Parameter,
    RequestBodyProperty,
)


class OpenApiParser:
    """Parses OpenAPI specification."""

    def __init__(self, spec_path: str) -> None:
        """Initialize parser with spec path."""
        self.spec_path = Path(spec_path)
        self.spec = self._load_spec()

    def _load_spec(self) -> dict[str, Any]:
        """Load OpenAPI spec from file (JSON or YAML)."""
        with open(self.spec_path) as f:
            content = f.read()

        # Try JSON first, then YAML
        if self.spec_path.suffix.lower() == ".json":
            result = json.loads(content)
            return dict(result) if isinstance(result, dict) else {}
        elif self.spec_path.suffix.lower() in (".yaml", ".yml"):
            result = yaml.safe_load(content)
            return dict(result) if isinstance(result, dict) else {}
        else:
            # Try to detect format
            try:
                result = json.loads(content)
                return dict(result) if isinstance(result, dict) else {}
            except json.JSONDecodeError:
                result = yaml.safe_load(content)
                return dict(result) if isinstance(result, dict) else {}

    def parse(
        self,
        exclude_tags: list[str] | None = None,
        include_tags: list[str] | None = None,
        tag_mapping: dict[str, str] | None = None,
    ) -> dict[str, CommandGroup]:
        """Parse the OpenAPI spec into command groups."""
        exclude_tags = exclude_tags or []
        include_tags = include_tags or []
        tag_mapping = tag_mapping or {}

        groups: dict[str, CommandGroup] = {}

        for path, path_item in self.spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue

                tags = operation.get("tags", ["default"])
                for tag in tags:
                    if tag in exclude_tags:
                        continue
                    if include_tags and tag not in include_tags:
                        continue

                    if tag not in groups:
                        cli_name = tag_mapping.get(tag, self._tag_to_cli_name(tag))
                        groups[tag] = CommandGroup(
                            name=tag,
                            cli_name=cli_name,
                            description=self._get_tag_description(tag),
                        )

                    op = self._parse_operation(path, method, operation)
                    groups[tag].operations.append(op)

        return groups

    def _tag_to_cli_name(self, tag: str) -> str:
        """Convert tag name to CLI-friendly name."""
        return tag.lower().replace(" ", "-")

    def _get_tag_description(self, tag: str) -> str:
        """Get tag description from spec."""
        for tag_def in self.spec.get("tags", []):
            if tag_def.get("name") == tag:
                desc = tag_def.get("description", f"{tag} commands")
                return str(desc)
        return f"{tag} commands"

    def _parse_operation(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> Operation:
        """Parse a single operation."""
        parameters = []
        for param in operation.get("parameters", []):
            parameters.append(self._parse_parameter(param))

        body_properties: list[RequestBodyProperty] = []
        if "requestBody" in operation:
            body_properties = self._parse_request_body(operation["requestBody"])

        return Operation(
            operation_id=operation.get("operationId", f"{method}_{path}"),
            method=method.upper(),
            path=path,
            summary=operation.get("summary", ""),
            description=operation.get("description", ""),
            tags=operation.get("tags", []),
            parameters=parameters,
            body_properties=body_properties,
        )

    def _parse_parameter(self, param: dict[str, Any]) -> Parameter:
        """Parse a parameter definition."""
        schema = param.get("schema", {})
        return Parameter(
            name=param["name"],
            location=param["in"],
            param_type=schema.get("type", "string"),
            required=param.get("required", False),
            description=param.get("description", ""),
            default=schema.get("default"),
            enum=schema.get("enum", []),
        )

    def _parse_request_body(self, body: dict[str, Any]) -> list[RequestBodyProperty]:
        """Parse request body definition into properties."""
        content = body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})

        # Handle $ref
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        if not schema:
            return []

        required_props = schema.get("required", [])
        properties = []

        for prop_name, prop_schema in schema.get("properties", {}).items():
            properties.append(
                RequestBodyProperty(
                    name=prop_name,
                    prop_type=prop_schema.get("type", "string"),
                    required=prop_name in required_props,
                    description=prop_schema.get("description", ""),
                )
            )

        return properties

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        """Resolve a $ref to its schema."""
        parts = ref.split("/")
        if len(parts) != 4 or parts[1] != "components":
            return {}

        schema_name = parts[3]
        result = self.spec.get("components", {}).get("schemas", {}).get(schema_name, {})
        return dict(result) if isinstance(result, dict) else {}
