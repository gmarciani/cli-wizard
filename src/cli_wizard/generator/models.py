# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Data models for CLI generation."""

import keyword
import re
from dataclasses import dataclass, field
from typing import Any

# Click type -> the placeholder Click's help shows after the option, which the
# generated README repeats so the two never disagree.
_METAVARS = {"str": "TEXT", "int": "INTEGER", "float": "FLOAT", "bool": "BOOLEAN"}

# The long options every generated command already takes: those declared in
# the generated options.py, plus Click's own --help. A spec option named like
# one would be consumed by both, so it is renamed by _cli_name.
COMMON_OPTION_NAMES = frozenset(
    {
        "profile",
        "debug",
        "base-url",
        "no-verify-ssl",
        "ca-file",
        "timeout",
        "header",
        "output",
        "help",
    }
)


def _python_name(name: str) -> str:
    """Convert a wire name to a snake_case identifier usable as an argument.

    A keyword, such as the `from` of a date range, gets a trailing underscore,
    or the generated function signature does not parse.
    """
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).lower().replace("-", "_")
    return f"{name}_" if keyword.iskeyword(name) else name


def _cli_name(name: str) -> str:
    """Convert a wire name to a kebab-case option name."""
    return re.sub(r"([a-z])([A-Z])", r"\1-\2", name).lower().replace("_", "-")


def _option_name(name: str, location: str, negatable: bool = False) -> str:
    """Get the name a spec option is derived from, distinct from a common option.

    A name taken by a common option, or whose `--no-` form is taken when the
    option is a flag pair, is prefixed with where the value goes, so `output`
    in the query becomes `--query-output`. The argument is renamed with it:
    Click stores both options under their argument name, and the last one
    given would set both.
    """
    cli_name = _cli_name(name)
    taken = {cli_name, f"no-{cli_name}"} if negatable else {cli_name}
    return f"{location}-{name}" if taken & COMMON_OPTION_NAMES else name


def _option_declarations(flag: str, cli_name: str, python_name: str) -> list[str]:
    """Get the declarations of a generated Click option.

    Click names the argument after the option, so when the Python name is not
    what Click derives from it, the option must declare that name as well.
    """
    if cli_name.replace("-", "_") == python_name:
        return [flag]
    return [flag, python_name]


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
        return _cli_name(_option_name(self.name, self.location))

    @property
    def python_name(self) -> str:
        """Get Python-friendly parameter name (snake_case)."""
        return _python_name(_option_name(self.name, self.location))

    @property
    def option_declarations(self) -> list[str]:
        """Get the declarations of the generated Click option."""
        return _option_declarations(
            f"--{self.cli_name}", self.cli_name, self.python_name
        )

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
    def metavar(self) -> str:
        """Get the value placeholder shown after the option in the documentation.

        An enum lists its choices the way Click renders a Choice; anything else
        names the type of one value, which for an array is the type of an item.
        """
        if self.enum:
            return f"[{'|'.join(self.enum)}]"
        return _METAVARS[self.click_type]

    @property
    def default_literal(self) -> str:
        """Get the default as a Python literal for the generated option.

        A string must be quoted, or the generated module names an undefined
        variable; numbers, booleans and lists keep their type.
        """
        return repr(self.default)

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
    default: Any = None
    # Signals that the value is a credential, read by _sensitive_field_names
    spec_format: str = ""
    write_only: bool = False

    @property
    def cli_name(self) -> str:
        """Get CLI-friendly name (kebab-case)."""
        return _cli_name(self._option_name)

    @property
    def python_name(self) -> str:
        """Get Python-friendly name (snake_case)."""
        return _python_name(self._option_name)

    @property
    def _option_name(self) -> str:
        """Get the name the option is derived from; a boolean is a flag pair."""
        negatable = self.click_type == "bool" and not self.is_array
        return _option_name(self.name, "body", negatable)

    @property
    def option_declarations(self) -> list[str]:
        """Get the declarations of the generated Click option.

        A boolean is a tri-state `--x/--no-x` flag, an array never is.
        """
        if self.click_type == "bool" and not self.is_array:
            flag = f"--{self.cli_name}/--no-{self.cli_name}"
        else:
            flag = f"--{self.cli_name}"
        return _option_declarations(flag, self.cli_name, self.python_name)

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
    def metavar(self) -> str:
        """Get the value placeholder shown after the option in the documentation."""
        return _METAVARS[self.click_type]

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
