# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Loading of the generation configuration, the project-level cli-wizard.yaml.

Shared by ``generate`` and ``bootstrap``, which read the same file the same
way: validated against the schema, then with its ``#[Param]`` references
expanded. Not to be confused with the tool's own settings in configuration.py.
"""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from cli_wizard.config.schema import Config
from cli_wizard.errors import ConfigError


def load_cli_config(
    config_path: Path | None, overrides: dict[str, Any] | None = None
) -> dict:
    """Load and validate the generator configuration.

    Without a file every parameter takes its schema default. ``overrides``
    are the values given on the command line and win over the file; they are
    applied before validation so the derived names follow them.
    """
    raw_config: dict[str, Any] = {}
    if config_path:
        try:
            with open(config_path) as f:
                raw_config = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            raise ConfigError(f"Could not load config file: {e}") from e
    raw_config.update(overrides or {})

    # Validate with Pydantic schema
    try:
        validated = Config(**raw_config)
        config = validated.model_dump()
    except ValidationError as e:
        problems = [
            f"  • {'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}"
            for error in e.errors()
        ]
        raise ConfigError("\n".join(["Invalid configuration:", *problems])) from e

    # Expand #[Param] references
    try:
        return expand_config_references(config)
    except ValueError as e:
        raise ConfigError(f"Invalid configuration:\n  • {e}") from e


def expand_config_references(config: dict[str, Any]) -> dict[str, Any]:
    """Expand #[Param] references in config values recursively.

    Supports referencing other config parameters using #[ParamName] syntax.
    Environment variables using ${VAR} syntax are left as-is for runtime expansion.
    References to unknown or non-string parameters are left as-is. A parameter
    that references itself, directly or through other parameters, raises a
    ValueError rather than expanding forever.
    """
    pattern = re.compile(r"#\[(\w+)\]")
    resolved: dict[str, str] = {}

    def resolve(name: str, chain: tuple[str, ...]) -> str:
        """Resolve a top-level parameter, refusing to expand it into itself."""
        if name in chain:
            path = " -> ".join(chain + (name,))
            raise ValueError(
                f"Circular #[Param] reference in configuration: {path} "
                f'(value of {name!r}: "{config[name]}")'
            )
        if name not in resolved:
            resolved[name] = substitute(config[name], chain + (name,))
        return resolved[name]

    def substitute(value: str, chain: tuple[str, ...]) -> str:
        def replace(match: re.Match[str]) -> str:
            param_name = match.group(1)
            if isinstance(config.get(param_name), str):
                return resolve(param_name, chain)
            return match.group(0)

        return pattern.sub(replace, value)

    def expand_value(value: Any) -> Any:
        if isinstance(value, str):
            return substitute(value, ())
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        return value

    return {key: expand_value(value) for key, value in config.items()}
