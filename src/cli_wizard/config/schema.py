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

import re
from typing import Literal, Any, get_type_hints, get_origin, get_args

from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo


class Config(BaseModel):
    """CLI Wizard configuration schema."""

    # Project identification (prompted during bootstrap)
    ProjectName: str = Field(
        default="My Project",
        description="Human-readable project name (title case)",
    )
    CommandName: str = Field(
        default="my-project",
        description="CLI command name (kebab-case)",
    )
    PackageName: str = Field(
        default="my_project",
        description="Python package name (snake_case)",
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
        description="Minimum Python version",
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
    OpenapiSpec: str = Field(
        default="openapi.json",
        description="Path to OpenAPI spec (relative to config file or absolute)",
    )
    ExcludeTags: list[str] = Field(
        default_factory=list,
        description="Tags to exclude from generation",
    )
    IncludeTags: list[str] = Field(
        default_factory=list,
        description="Tags to include (if empty, all non-excluded tags are included)",
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
        description="Log color style: 'full' colors entire line, 'level' colors only the level prefix",
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
        description="CA certificate file for SSL verification (relative to config or absolute)",
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
                return field_info.default_factory()
        return None
