# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Generate command for CLI Wizard."""

import click
import logging
from pathlib import Path

import yaml

from cli_wizard.config.configuration import load_default_config
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
@click.option(
    "--name",
    "-n",
    type=str,
    default=None,
    help="CLI name (default: from config or 'my-cli')",
)
@click.pass_context
def generate(
    ctx: click.Context,
    working_dir: str | None,
    openapi: str,
    config: str,
    output: str,
    name: str | None,
) -> None:
    """Generate a CLI from an OpenAPI spec and config file."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    # Resolve paths relative to working directory
    base_dir = Path(working_dir) if working_dir else Path.cwd()
    openapi_path = (
        base_dir / openapi if not Path(openapi).is_absolute() else Path(openapi)
    )
    config_path = base_dir / config if not Path(config).is_absolute() else Path(config)
    output_path = base_dir / output if not Path(output).is_absolute() else Path(output)

    if debug:
        logger.debug(f"Working directory: {base_dir}")
        logger.debug(f"OpenAPI spec: {openapi_path}")
        logger.debug(f"Config file: {config_path}")
        logger.debug(f"Output directory: {output_path}")

    # Validate input files exist
    if not openapi_path.exists():
        click.secho(
            f"✗ OpenAPI spec file not found: {openapi_path}", fg="red", err=True
        )
        raise SystemExit(1)
    if not config_path.exists():
        click.secho(f"✗ Config file not found: {config_path}", fg="red", err=True)
        raise SystemExit(1)

    # Load configuration
    cli_config = _load_cli_config(config_path)
    gen_config = cli_config.get("generator", {})

    # Determine CLI name and package name
    cli_name = name or cli_config.get("cli", {}).get("name", "my-cli")
    package_name = cli_name.replace("-", "_")

    # Parse OpenAPI spec
    click.secho("📄 Parsing OpenAPI spec: ", fg="cyan", nl=False)
    click.echo(openapi_path)
    parser = OpenApiParser(str(openapi_path))

    groups = parser.parse(
        exclude_tags=gen_config.get("exclude_tags", []),
        include_tags=gen_config.get("include_tags", []),
        tag_mapping=cli_config.get("tag_mapping", {}),
    )

    if not groups:
        click.secho("✗ No operations found in OpenAPI spec", fg="red", err=True)
        raise SystemExit(1)

    # Generate CLI project
    click.secho("⚙️  Generating CLI project: ", fg="cyan", nl=False)
    click.echo(output_path)
    generator = CliGenerator(config=cli_config)
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
    click.echo(f"   cd {output_path}")
    click.echo("   pip install -e .")
    click.echo(f"   {cli_name} --help")


def _load_cli_config(config_path: Path) -> dict:
    """Load CLI generator configuration from YAML file."""
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        logger.warning(f"Could not load config file: {e}")
        return {}
