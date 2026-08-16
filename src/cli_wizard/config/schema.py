# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration schema for CLI Wizard.

This schema is the single source of truth for:
- Parameter names (PascalCase)
- Parameter descriptions (used in prompts and generated config comments)
- Default values
- Validation rules

The schema parameters are used directly as Jinja2 template variables.
"""

import keyword
import re
from datetime import date
from typing import Any, Literal, get_args, get_origin, get_type_hints

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.fields import FieldInfo

# Supported Python versions, oldest first. Adding one means updating tox.ini
# and .github/workflows/test.yaml too; the tests fail if they disagree.
SUPPORTED_PYTHON_VERSIONS: tuple[str, ...] = ("3.12", "3.13", "3.14")


def python_versions_from(minimum: str) -> list[str]:
    """Return the supported versions at or above ``minimum``, oldest first.

    A generated project declaring ``PythonVersion: "3.13"`` must not claim
    3.12 support in its classifiers, tox envlist or CI matrix, so all four are
    derived from this rather than hardcoded.
    """
    if minimum not in SUPPORTED_PYTHON_VERSIONS:
        raise ValueError(
            f"Unsupported Python version: {minimum}. "
            f"Supported versions are {', '.join(SUPPORTED_PYTHON_VERSIONS)}."
        )
    return list(SUPPORTED_PYTHON_VERSIONS[SUPPORTED_PYTHON_VERSIONS.index(minimum) :])


def tox_env_name(version: str) -> str:
    """Convert a ``3.12``-style version to its ``py312`` tox environment name."""
    return "py" + version.replace(".", "")


def ruff_target_version(version: str) -> str:
    """Convert a ``3.12``-style version to ruff's ``py312`` target-version."""
    return "py" + version.replace(".", "")


class Config(BaseModel):
    """CLI Wizard configuration schema."""

    # Project identification (prompted during bootstrap)
    ProjectName: str = Field(
        default="My Project",
        description="Human-readable project name (title case)",
    )
    CommandName: str | None = Field(
        default=None,
        description=(
            "CLI command name (kebab-case, derived from ProjectName if not set)"
        ),
    )
    PackageName: str | None = Field(
        default=None,
        description=(
            "Python package name (snake_case, derived from ProjectName if not set)"
        ),
    )
    Description: str = Field(
        default="A CLI application",
        description="Project description",
    )
    Version: str = Field(
        default="1.0.0",
        description="Project version",
    )

    # Author information (prompted during bootstrap)
    AuthorName: str = Field(
        default="Your Name",
        description="Author name",
    )
    AuthorEmail: str = Field(
        default="your.email@example.com",
        description="Author email",
    )
    GithubUser: str = Field(
        default="username",
        description="GitHub username",
    )

    # Python settings (prompted during bootstrap)
    PythonVersion: str = Field(
        default="3.12",
        description=(
            f"Minimum Python version, one of {', '.join(SUPPORTED_PYTHON_VERSIONS)}"
        ),
    )

    # API settings (prompted during bootstrap)
    DefaultBaseUrl: str = Field(
        default="http://localhost:3000",
        description="Default API base URL",
    )

    # Output settings
    MainDir: str = Field(
        default="${HOME}/.#[CommandName]",
        description="Main directory for CLI data (config, cache, logging, etc.)",
    )
    ProfileFile: str = Field(
        default="#[MainDir]/profiles.yaml",
        description="Path to profiles YAML file",
    )

    # OpenAPI settings
    OpenapiSpec: str | None = Field(
        default=None,
        description="Path to OpenAPI spec (relative to config file or absolute)",
    )
    IncludeTags: list[str] = Field(
        default_factory=list,
        description="Tags to include (if empty, all non-excluded tags are included)",
    )
    ExcludeTags: list[str] = Field(
        default_factory=list,
        description="Tags to exclude from generation",
    )
    IncludeOperations: list[str] = Field(
        default_factory=list,
        description=(
            "Operation IDs to include (if empty, all non-excluded operations "
            "are included)"
        ),
    )
    ExcludeOperations: list[str] = Field(
        default_factory=list,
        description="Operation IDs to exclude from generation",
    )
    TagMapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map OpenAPI tags to CLI command group names",
    )
    CommandMapping: dict[str, str] = Field(
        default_factory=dict,
        description="Customize command names (operationId -> command name)",
    )

    # Output formatting
    OutputFormat: Literal["json", "table", "yaml"] = Field(
        default="json",
        description="Default output format",
    )
    OutputColors: bool = Field(
        default=True,
        description="Enable colored output",
    )
    JsonIndent: int = Field(
        default=2,
        ge=0,
        description="JSON indentation",
    )
    TableStyle: Literal["ascii", "rounded", "minimal", "markdown"] = Field(
        default="rounded",
        description="Table style",
    )

    # Splash screen
    SplashFile: str | None = Field(
        default=None,
        description="Path to splash text file (relative to config or absolute)",
    )
    SplashColor: str = Field(
        default="#FFFFFF",
        description="Color for splash text (hex code)",
    )

    # Logging
    LogLevel: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Default log level",
    )
    LogFormat: str = Field(
        default="%(asctime)s [%(levelname)s] %(message)s",
        description="Log message format (Python logging format)",
    )
    LogTimestampFormat: str = Field(
        default="%Y-%m-%dT%H:%M:%S",
        description="Timestamp format for log messages (strftime format)",
    )
    LogTimezone: Literal["UTC", "Local"] = Field(
        default="UTC",
        description="Timezone for log timestamps",
    )
    LogColorStyle: Literal["full", "level"] = Field(
        default="level",
        description=(
            "Log color style: 'full' colors entire line, 'level' colors only "
            "the level prefix"
        ),
    )
    LogColorDebug: str = Field(
        default="#808080",
        description="Color for DEBUG log level (hex code)",
    )
    LogColorInfo: str = Field(
        default="#00FF00",
        description="Color for INFO log level (hex code)",
    )
    LogColorWarning: str = Field(
        default="#FFFF00",
        description="Color for WARNING log level (hex code)",
    )
    LogColorError: str = Field(
        default="#FF0000",
        description="Color for ERROR log level (hex code)",
    )
    LogFile: str | None = Field(
        default=None,
        description="Path to log file (None means no file logging)",
    )
    LogRotationType: Literal["size", "days"] = Field(
        default="days",
        description="Log rotation type: 'size' for file size, 'days' for time-based",
    )
    LogRotationSize: int = Field(
        default=10,
        ge=1,
        description="Log rotation size in MB (when LogRotationType is 'size')",
    )
    LogRotationDays: int = Field(
        default=30,
        ge=1,
        description="Log rotation interval in days (when LogRotationType is 'days')",
    )
    LogRotationBackupCount: int = Field(
        default=5,
        ge=0,
        description="Number of backup log files to keep",
    )

    # API client settings
    Timeout: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds",
    )
    CaFile: str | None = Field(
        default=None,
        description=(
            "CA certificate file for SSL verification (relative to config or absolute)"
        ),
    )
    RetryMaxAttempts: int = Field(
        default=3,
        ge=0,
        description="Retry max attempts",
    )
    RetryBackoffFactor: float = Field(
        default=0.5,
        ge=0,
        description="Retry backoff factor",
    )

    # Generation options
    IncludeGithubWorkflows: bool = Field(
        default=False,
        description="Include .github folder with workflows, issue templates, etc.",
    )
    CoverageThreshold: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Minimum test coverage percentage to enforce (0 disables it)",
    )

    # Copyright
    CopyrightYear: int | None = Field(
        default=None,
        description="Copyright year for LICENSE and other files",
    )

    # Repository
    RepositoryUrl: str | None = Field(
        default=None,
        description="Repository URL for the project",
    )
    HomePageUrl: str | None = Field(
        default=None,
        description=(
            "Home page URL for the project, such as a documentation site. "
            "Defaults to RepositoryUrl"
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def derive_names_from_project(cls, data: Any) -> Any:
        """Derive optional fields that have a sensible value from the others.

        These derivations live here rather than in the bootstrap prompts so
        that ``generate`` gets them too. Leaving them unset previously
        rendered "Copyright (c) None" and 'Homepage = "None"' into generated
        projects.
        """
        if isinstance(data, dict):
            # An explicit null must fall back too, not just a missing key: a
            # config carrying "ProjectName: null" would otherwise reach re.sub
            # as None and raise TypeError instead of a ValidationError.
            project_name = data.get("ProjectName") or "My Project"
            if not data.get("CommandName"):
                data["CommandName"] = (
                    re.sub(r"[^a-zA-Z0-9]+", "-", project_name).strip("-").lower()
                )
            if not data.get("PackageName"):
                data["PackageName"] = (
                    re.sub(r"[^a-zA-Z0-9]+", "_", project_name).strip("_").lower()
                )
            if not data.get("CopyrightYear"):
                data["CopyrightYear"] = date.today().year
            if not data.get("RepositoryUrl"):
                github_user = data.get("GithubUser") or cls.get_field_default(
                    "GithubUser"
                )
                data["RepositoryUrl"] = (
                    f"https://github.com/{github_user}/{data['CommandName']}"
                )
            if not data.get("HomePageUrl"):
                data["HomePageUrl"] = data["RepositoryUrl"]
        return data

    @field_validator("PythonVersion")
    @classmethod
    def validate_python_version(cls, v: str) -> str:
        """Validate that PythonVersion is one cli-wizard can generate for.

        An unsupported value used to flow straight into requires-python and
        the mypy config, producing a project that claims support cli-wizard
        never tested and cannot express in its version matrix.
        """
        if v not in SUPPORTED_PYTHON_VERSIONS:
            raise ValueError(
                f"Unsupported Python version: {v}. Supported versions are "
                f"{', '.join(SUPPORTED_PYTHON_VERSIONS)}."
            )
        return v

    @field_validator("PackageName")
    @classmethod
    def validate_package_name(cls, v: str | None) -> str | None:
        """Validate that PackageName is usable as a Python package name.

        The generated project imports itself by this name, so anything that
        is not a valid identifier produces source code that does not parse.
        """
        if v is None:
            return v
        if not v.isidentifier() or keyword.iskeyword(v):
            raise ValueError(
                f"'{v}' is not a valid Python package name. It must be a valid "
                "Python identifier, for example 'my_cli' rather than 'my-cli'."
            )
        return v

    @field_validator(
        "SplashColor",
        "LogColorDebug",
        "LogColorInfo",
        "LogColorWarning",
        "LogColorError",
    )
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        """Validate that color is a valid hex color code."""
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError(f"Invalid hex color code: {v}. Must be in format #RRGGBB")
        return v.upper()

    model_config = {"extra": "forbid"}

    @classmethod
    def get_field_info(cls, field_name: str) -> FieldInfo | None:
        """Get field info for a specific field."""
        return cls.model_fields.get(field_name)

    @classmethod
    def get_field_description(cls, field_name: str) -> str:
        """Get the description for a specific field."""
        field_info = cls.get_field_info(field_name)
        if field_info and field_info.description:
            return field_info.description
        return ""

    @classmethod
    def get_field_default(cls, field_name: str) -> Any:
        """Get the default value for a specific field."""
        field_info = cls.get_field_info(field_name)
        if field_info:
            if field_info.default is not None:
                return field_info.default
            if field_info.default_factory is not None:
                return field_info.default_factory()  # type: ignore[call-arg]
        return None

    @classmethod
    def parse_cli_value(cls, field_name: str, raw: str) -> Any:
        """Convert a raw CLI string argument into a value for ``field_name``.

        Click arguments always arrive as strings. List fields accept a
        comma-separated string; mapping fields have no sensible
        single-argument form. Scalars are left for Pydantic to coerce.

        Raises:
            ValueError: if the field is unknown or cannot be set from the CLI.
        """
        field_info = cls.get_field_info(field_name)
        if field_info is None:
            raise ValueError(f"'{field_name}' is not a configuration key")

        origin = get_origin(field_info.annotation)
        if origin is list:
            # An empty string clears the list; there is no other way to do it.
            return [item.strip() for item in raw.split(",") if item.strip()]
        if origin is dict:
            raise ValueError(
                f"'{field_name}' is a mapping and cannot be set from the command "
                "line. Edit the configuration file directly."
            )
        return raw

    @classmethod
    def get_all_fields_metadata(cls) -> list[dict[str, Any]]:
        """Get metadata for all fields in schema order.

        Returns a list of dicts with: name, description, default, type_hint
        """
        from pydantic_core import PydanticUndefined

        fields_metadata = []
        type_hints = get_type_hints(cls)

        for field_name, field_info in cls.model_fields.items():
            # Handle default values properly
            if field_info.default is not PydanticUndefined:
                default = field_info.default
            elif field_info.default_factory is not None:
                default = field_info.default_factory()  # type: ignore[call-arg]
            else:
                default = None

            # Get type hint for display
            type_hint = type_hints.get(field_name)
            type_str = cls._format_type_hint(type_hint)

            fields_metadata.append(
                {
                    "name": field_name,
                    "description": field_info.description or "",
                    "default": default,
                    "type_hint": type_str,
                }
            )

        return fields_metadata

    @classmethod
    def _format_type_hint(cls, type_hint: Any) -> str:
        """Format a type hint for display in comments."""
        import types

        if type_hint is None:
            return "Any"

        origin = get_origin(type_hint)
        args = get_args(type_hint)

        if origin is Literal:
            return "one of: " + ", ".join(repr(a) for a in args)
        elif origin is list:
            return "list"
        elif origin is dict:
            return "dict"
        # Handle Union types (including Optional which is Union[X, None])
        elif origin is types.UnionType:
            # Filter out NoneType for cleaner display
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                return cls._format_type_hint(non_none_args[0]) + " (optional)"
            return " | ".join(cls._format_type_hint(a) for a in non_none_args)
        elif hasattr(type_hint, "__name__"):
            return str(type_hint.__name__)
        else:
            # Handle str | None style unions in string form
            type_str = str(type_hint)
            if " | None" in type_str:
                return type_str.replace(" | None", "") + " (optional)"
            return type_str
