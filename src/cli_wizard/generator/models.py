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
    items_type: str | None = None
    # Signals that the value is a credential, read by _sensitive_field_names
    spec_format: str = ""
    write_only: bool = False

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
    def is_array(self) -> bool:
        """Whether this parameter accepts multiple values."""
        return self.param_type == "array"

    @property
    def click_type(self) -> str:
        """Get Click type for this parameter, or for its items when an array."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
        }
        source = (self.items_type or "string") if self.is_array else self.param_type
        return type_map.get(source, "str")

    @property
    def python_annotation(self) -> str:
        """Get the annotation for the generated function argument.

        Click hands a tuple to a `multiple=True` option, empty when the option
        is omitted, so an array is never optional. Neither is a parameter
        carrying a default, which Click supplies whenever the user does not.
        """
        if self.is_array:
            return f"tuple[{self.click_type}, ...]"
        if self.required or self.default is not None:
            return self.click_type
        return f"{self.click_type} | None"


@dataclass
class RequestBodyProperty:
    """Represents a request body property."""

    name: str
    prop_type: str
    required: bool
    description: str = ""
    items_type: str | None = None
    # Signals that the value is a credential, read by _sensitive_field_names
    spec_format: str = ""
    write_only: bool = False

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
    def is_array(self) -> bool:
        """Whether this property accepts multiple values."""
        return self.prop_type == "array"

    @property
    def click_type(self) -> str:
        """Get Click type, or the type of the items when an array."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
        }
        source = (self.items_type or "string") if self.is_array else self.prop_type
        return type_map.get(source, "str")

    @property
    def python_annotation(self) -> str:
        """Get the annotation for the generated function argument.

        Click hands a tuple to a `multiple=True` option, empty when the option
        is omitted, so an array is never optional.
        """
        if self.is_array:
            return f"tuple[{self.click_type}, ...]"
        return self.click_type if self.required else f"{self.click_type} | None"


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
    def path_parameters(self) -> list["Parameter"]:
        """Get the parameters carried in the URL path."""
        return [p for p in self.parameters if p.location == "path"]

    @property
    def query_parameters(self) -> list["Parameter"]:
        """Get the parameters carried in the query string."""
        return [p for p in self.parameters if p.location == "query"]

    @property
    def _base_operation_id(self) -> str:
        """Get the base operation ID without the module path.

        For example 'server.get_greetings' becomes 'get_greetings'.
        """
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

    @property
    def has_path_parameters(self) -> bool:
        """Whether any operation in the group takes a path parameter.

        The generated module only imports the path encoder when it has
        something to encode.
        """
        return any(op.path_parameters for op in self.operations)
