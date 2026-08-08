# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Generate command for CLI Wizard."""

import logging
import re
import shutil
from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import ValidationError

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.generator import CliGenerator, OpenApiParser
from cli_wizard.generator.generator import RuffNotFoundError, resolve_ruff

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
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt if output directory exists and is not empty",
)
@click.pass_context
def generate(
    ctx: click.Context,
    path: str,
    configuration: str,
    api: str | None,
    force: bool,
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
            include_operations=cli_config.get("IncludeOperations", []),
            exclude_operations=cli_config.get("ExcludeOperations", []),
        )

        if not groups:
            click.secho("⚠️  No operations found in OpenAPI spec", fg="yellow")
    else:
        click.secho(
            "ℹ️  No OpenAPI spec provided, generating CLI without API commands",
            fg="cyan",
        )

    # Verify the formatter before deleting the previous output
    try:
        resolve_ruff()
    except RuffNotFoundError as e:
        click.secho(f"✗ {e}", fg="red", err=True)
        raise SystemExit(1)

    # Clean up output directory before generating
    if output_path.exists():
        # Check if we're inside the output directory
        try:
            cwd = Path.cwd()
            if output_path in cwd.parents or output_path == cwd:
                click.secho(
                    "✗ Cannot clean output directory while inside it. "
                    "Please run from a different directory.",
                    fg="red",
                    err=True,
                )
                raise SystemExit(1)
        except OSError:
            # Current directory may already be deleted
            pass

        # Confirm before destroying a directory that holds work
        if not force and any(output_path.iterdir()):
            click.confirm(
                f"⚠️  Output directory '{output_path}' is not empty. "
                "Its entire contents will be deleted. Continue?",
                abort=True,
            )

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
    try:
        return _expand_config_references(config)
    except ValueError as e:
        click.secho("✗ Invalid configuration:", fg="red", err=True)
        click.secho(f"  • {e}", fg="red", err=True)
        raise SystemExit(1)


def _expand_config_references(config: dict[str, Any]) -> dict[str, Any]:
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
