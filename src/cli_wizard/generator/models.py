# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Data models for CLI generation."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Parameter:
    """Represents an API parameter."""

    name: str
    location: str  # path, query, header
    param_type: str
    required: bool
    description: str = ""
    default: Any = None
    enum: list[str] = field(default_factory=list)

    @property
    def cli_name(self) -> str:
        """Get CLI-friendly parameter name (kebab-case)."""
        return re.sub(r"([a-z])([A-Z])", r"\1-\2", self.name).lower().replace("_", "-")

    @property
    def python_name(self) -> str:
        """Get Python-friendly parameter name (snake_case)."""
        name = re.sub(r"([a-z])([A-Z])", r"\1_\2", self.name).lower()
        return name.replace("-", "_")

    @property
    def click_type(self) -> str:
        """Get Click type for this parameter."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
        }
        return type_map.get(self.param_type, "str")


@dataclass
class RequestBodyProperty:
    """Represents a request body property."""

    name: str
    prop_type: str
    required: bool
    description: str = ""

    @property
    def cli_name(self) -> str:
        """Get CLI-friendly name (kebab-case)."""
        name = re.sub(r"([a-z])([A-Z])", r"\1-\2", self.name).lower()
        return name.replace("_", "-")

    @property
    def python_name(self) -> str:
        """Get Python-friendly name (snake_case)."""
        name = re.sub(r"([a-z])([A-Z])", r"\1_\2", self.name).lower()
        return name.replace("-", "_")

    @property
    def click_type(self) -> str:
        """Get Click type."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
        }
        return type_map.get(self.prop_type, "str")


@dataclass
class Operation:
    """Represents an API operation."""

    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    tags: list[str]
    parameters: list[Parameter]
    body_properties: list[RequestBodyProperty] = field(default_factory=list)

    @property
    def _base_operation_id(self) -> str:
        """Get the base operation ID without module path (e.g., 'server.get_greetings' -> 'get_greetings')."""
        if "." in self.operation_id:
            return self.operation_id.rsplit(".", 1)[-1]
        return self.operation_id

    @property
    def command_name(self) -> str:
        """Get CLI command name from operation ID (kebab-case)."""
        name = re.sub(r"(?<!^)(?=[A-Z])", "-", self._base_operation_id).lower()
        return name.replace("_", "-")

    @property
    def function_name(self) -> str:
        """Get Python function name from operation ID (snake_case)."""
        return self.command_name.replace("-", "_")


@dataclass
class CommandGroup:
    """Represents a group of commands (from a tag)."""

    name: str
    cli_name: str
    description: str
    operations: list[Operation] = field(default_factory=list)

    @property
    def module_name(self) -> str:
        """Get Python module name."""
        return self.cli_name.replace("-", "_")
