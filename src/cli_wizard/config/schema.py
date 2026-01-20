# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Configuration schema for CLI Wizard."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """CLI Wizard configuration schema."""

    # Required parameters
    PackageName: str = Field(
        ..., description="Python package name for the generated CLI"
    )
    DefaultBaseUrl: str = Field(..., description="Default API base URL")

    # Output settings
    OutputDir: str = Field(
        default="#[PackageName]",
        description="Output directory for the generated CLI project",
    )
    MainDir: str = Field(
        default="${HOME}/.#[PackageName]",
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
        default="[%(levelname)s] %(asctime)s %(message)s",
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
