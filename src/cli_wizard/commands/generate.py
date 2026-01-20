# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Generate command for CLI Wizard."""

import re
import click
import logging
import shutil
from pathlib import Path

import yaml
from pydantic import ValidationError

from cli_wizard.config.configuration import load_default_config
from cli_wizard.config.schema import Config
from cli_wizard.generator import OpenApiParser, CliGenerator

logger = logging.getLogger(__name__)

# Load defaults from config
_defaults = load_default_config()
_default_openapi = _defaults.get("OpenApiFileName", "openapi.yaml")
_default_config = _defaults.get("ConfigFileName", "config.yaml")
_default_output = _defaults.get("OutputDir", "cli")


@click.command()
@click.option(
    "--working-dir",
    "-w",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=None,
    help="Working directory for resolving relative paths",
)
@click.option(
    "--openapi",
    "-o",
    type=click.Path(dir_okay=False),
    default=_default_openapi,
    help=f"Path to OpenAPI spec file in YAML or JSON format (default: {_default_openapi})",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(dir_okay=False),
    default=_default_config,
    help=f"Path to config YAML file (default: {_default_config})",
)
@click.option(
    "--output",
    "-d",
    type=click.Path(file_okay=False),
    default=_default_output,
    help=f"Output directory for generated CLI (default: {_default_output})",
)
@click.pass_context
def generate(
    ctx: click.Context,
    working_dir: str | None,
    openapi: str,
    config: str,
    output: str,
) -> None:
    """Generate a CLI from an OpenAPI spec and config file."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    # Resolve paths relative to working directory
    base_dir = Path(working_dir) if working_dir else Path.cwd()
    openapi_path = (
        base_dir / openapi if not Path(openapi).is_absolute() else Path(openapi)
    )
    config_path = base_dir / config if not Path(config).is_absolute() else Path(config)

    if debug:
        logger.debug(f"Working directory: {base_dir}")
        logger.debug(f"OpenAPI spec: {openapi_path}")
        logger.debug(f"Config file: {config_path}")

    # Validate input files exist
    if not openapi_path.exists():
        click.secho(
            f"✗ OpenAPI spec file not found: {openapi_path}", fg="red", err=True
        )
        raise SystemExit(1)
    if not config_path.exists():
        click.secho(f"✗ Config file not found: {config_path}", fg="red", err=True)
        raise SystemExit(1)

    # Load and validate configuration
    cli_config = _load_cli_config(config_path)

    # Resolve output path (CLI option > config > default)
    output_dir = output
    if output == _default_output and cli_config.get("OutputDir"):
        output_dir = cli_config.get("OutputDir")
    output_path = (
        base_dir / output_dir
        if not Path(output_dir).is_absolute()
        else Path(output_dir)
    )

    if debug:
        logger.debug(f"Output directory: {output_path}")

    # Get CLI name and package name from config
    cli_name = cli_config["PackageName"]
    # Convert hyphens to underscores for Python package compatibility
    package_name = cli_name.replace("-", "_")

    # Parse OpenAPI spec
    click.secho("📄 Parsing OpenAPI spec: ", fg="cyan", nl=False)
    click.echo(openapi_path)
    parser = OpenApiParser(str(openapi_path))

    groups = parser.parse(
        exclude_tags=cli_config.get("ExcludeTags", []),
        include_tags=cli_config.get("IncludeTags", []),
        tag_mapping=cli_config.get("TagMapping", {}),
    )

    if not groups:
        click.secho("✗ No operations found in OpenAPI spec", fg="red", err=True)
        raise SystemExit(1)

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
    click.secho("  🔧 Commands: ", fg="white", nl=False)
    click.echo(f"{len(groups)} groups")
    for tag, group in groups.items():
        click.secho(f"     • {group.cli_name}", fg="yellow", nl=False)
        click.echo(f" ({len(group.operations)} commands)")

    click.echo()
    click.secho("📋 Next steps:", fg="cyan", bold=True)
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


def _expand_config_references(config: dict) -> dict:
    """Expand #[Param] references in config values recursively.

    Supports referencing other config parameters using #[ParamName] syntax.
    Environment variables using ${VAR} syntax are left as-is for runtime expansion.
    Recursively expands until no more references remain.
    """

    def expand_value(value: any, config: dict) -> any:
        if isinstance(value, str):
            # Keep expanding until no more #[Param] references
            pattern = r"#\[(\w+)\]"
            prev_value = None
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
    expanded = expand_value(config, config)

    # Second pass: re-expand with updated config to handle nested references
    return expand_value(expanded, expanded)
