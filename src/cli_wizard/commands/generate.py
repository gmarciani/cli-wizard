# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Generate command for CLI Wizard."""

import re
from typing import Any

import click
import logging
import shutil
from pathlib import Path

import yaml
from pydantic import ValidationError

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.generator import OpenApiParser, CliGenerator

logger = logging.getLogger(__name__)


@click.command(
    help="""Generate the CLI from config and OpenAPI spec.

PATH is the output directory where the CLI project will be generated.
It can be a relative or absolute path.

If --api is provided, API commands will be generated from the OpenAPI spec.
Otherwise, a functional CLI is generated without API commands."""
)
@click.argument(
    "path",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--configuration",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
    help=f"Path to {CONFIG_FILE_NAME} configuration file",
)
@click.option(
    "--api",
    "-a",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to OpenAPI spec file in YAML or JSON format (optional)",
)
@click.pass_context
def generate(
    ctx: click.Context,
    path: str,
    configuration: str,
    api: str | None,
) -> None:
    """Generate command implementation."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    output_path = Path(path)
    config_path = Path(configuration)

    if debug:
        logger.debug(f"Output directory: {output_path}")
        logger.debug(f"Config file: {config_path}")
        logger.debug(f"OpenAPI spec (CLI): {api}")

    # Load and validate configuration
    cli_config = _load_cli_config(config_path)

    # Resolve OpenAPI spec path: CLI option > config OpenapiSpec > None
    api_path: Path | None = None
    if api:
        api_path = Path(api)
    elif cli_config.get("OpenapiSpec"):
        # Resolve relative to config file directory
        spec_path = Path(cli_config["OpenapiSpec"])
        if not spec_path.is_absolute():
            spec_path = config_path.parent / spec_path
        if spec_path.exists():
            api_path = spec_path
        else:
            click.secho(
                f"⚠️  OpenapiSpec '{cli_config['OpenapiSpec']}' not found, "
                "generating CLI without API commands",
                fg="yellow",
            )

    if debug:
        logger.debug(f"OpenAPI spec (resolved): {api_path}")

    # Get CLI name and package name from config
    cli_name = cli_config["CommandName"]
    package_name = cli_config["PackageName"]

    # Parse OpenAPI spec if provided
    groups: dict = {}
    if api_path:
        click.secho("📄 Parsing OpenAPI spec: ", fg="cyan", nl=False)
        click.echo(api_path)
        parser = OpenApiParser(str(api_path))

        groups = parser.parse(
            exclude_tags=cli_config.get("ExcludeTags", []),
            include_tags=cli_config.get("IncludeTags", []),
            tag_mapping=cli_config.get("TagMapping", {}),
        )

        if not groups:
            click.secho("⚠️  No operations found in OpenAPI spec", fg="yellow")
    else:
        click.secho(
            "ℹ️  No OpenAPI spec provided, generating CLI without API commands",
            fg="cyan",
        )

    # Clean up output directory before generating
    if output_path.exists():
        # Check if we're inside the output directory
        try:
            cwd = Path.cwd()
            if output_path in cwd.parents or output_path == cwd:
                click.secho(
                    f"✗ Cannot clean output directory while inside it. "
                    f"Please run from a different directory.",
                    fg="red",
                    err=True,
                )
                raise SystemExit(1)
        except OSError:
            # Current directory may already be deleted
            pass
        click.secho("🧹 Cleaning output directory: ", fg="cyan", nl=False)
        click.echo(output_path)
        shutil.rmtree(output_path)

    # Generate CLI project
    click.secho("⚙️  Generating CLI project: ", fg="cyan", nl=False)
    click.echo(output_path)
    generator = CliGenerator(config=cli_config, config_dir=config_path.parent)
    generator.generate(groups, output_path, cli_name, package_name)

    # Summary
    click.secho(f"\n✓ Generated CLI '{cli_name}'", fg="green", bold=True)
    click.secho("  📁 Location: ", fg="white", nl=False)
    click.echo(output_path)
    click.secho("  📦 Package: ", fg="white", nl=False)
    click.echo(package_name)
    if groups:
        click.secho("  🔧 Commands: ", fg="white", nl=False)
        click.echo(f"{len(groups)} groups")
        for tag, group in groups.items():
            click.secho(f"     • {group.cli_name}", fg="yellow", nl=False)
            click.echo(f" ({len(group.operations)} commands)")
    else:
        click.secho("  🔧 Commands: ", fg="white", nl=False)
        click.echo("config only (no API commands)")

    click.echo()
    click.secho("📋 Validate:", fg="cyan", bold=True)
    click.echo(f"   pip install -e {output_path}")
    click.echo(f"   {cli_name} --help")


def _load_cli_config(config_path: Path) -> dict:
    """Load and validate CLI generator configuration from YAML file."""
    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        click.secho(f"✗ Could not load config file: {e}", fg="red", err=True)
        raise SystemExit(1)

    # Validate with Pydantic schema
    try:
        validated = Config(**raw_config)
        config = validated.model_dump()
    except ValidationError as e:
        click.secho("✗ Invalid configuration:", fg="red", err=True)
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            click.secho(f"  • {field}: {error['msg']}", fg="red", err=True)
        raise SystemExit(1)

    # Expand #[Param] references
    return _expand_config_references(config)


def _expand_config_references(config: dict[str, Any]) -> dict[str, Any]:
    """Expand #[Param] references in config values recursively.

    Supports referencing other config parameters using #[ParamName] syntax.
    Environment variables using ${VAR} syntax are left as-is for runtime expansion.
    Recursively expands until no more references remain.
    """

    def expand_value(value: Any, config: dict[str, Any]) -> Any:
        if isinstance(value, str):
            # Keep expanding until no more #[Param] references
            pattern = r"#\[(\w+)\]"
            prev_value: str | None = None
            while prev_value != value:
                prev_value = value
                matches = re.findall(pattern, value)
                for param_name in matches:
                    if param_name in config:
                        replacement = config[param_name]
                        if isinstance(replacement, str):
                            value = value.replace(f"#[{param_name}]", replacement)
            return value
        elif isinstance(value, dict):
            return {k: expand_value(v, config) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item, config) for item in value]
        return value

    # First pass: expand all values
    expanded: dict[str, Any] = expand_value(config, config)

    # Second pass: re-expand with updated config to handle nested references
    result: dict[str, Any] = expand_value(expanded, expanded)
    return result
