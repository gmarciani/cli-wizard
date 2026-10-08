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
    help="""Generate the CLI from an OpenAPI spec.

API commands are generated from the OpenAPI spec given with --api or with the
Api parameter of the configuration file. Without either, a functional CLI is
generated without API commands.

A configuration file is optional: without one, --project-name names the
project and every other parameter takes its default.

The project is written to the --output directory, by default a directory named
after CommandName next to the configuration file, or in the current directory
when there is no configuration file. Its previous contents are deleted."""
)
@click.option(
    "--api",
    "-a",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to the OpenAPI spec file, YAML or JSON",
)
@click.option(
    "--project-name",
    "-p",
    default=None,
    help="Human-readable project name; CommandName and PackageName derive from it",
)
@click.option(
    "--configuration",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help=f"Path to {CONFIG_FILE_NAME} configuration file",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, resolve_path=True),
    default=None,
    help="Output directory (default: CommandName next to the configuration file)",
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
    api: str | None,
    project_name: str | None,
    configuration: str | None,
    output: str | None,
    force: bool,
) -> None:
    """Generate command implementation."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    config_path = Path(configuration) if configuration else None
    config_dir = config_path.parent if config_path else Path.cwd()

    if debug:
        logger.debug(f"Config file: {config_path}")
        logger.debug(f"Project name (CLI): {project_name}")
        logger.debug(f"OpenAPI spec (CLI): {api}")
        logger.debug(f"Output directory (CLI): {output}")

    # Load and validate configuration
    overrides = {"ProjectName": project_name} if project_name else {}
    cli_config = _load_cli_config(config_path, overrides)
    output_path = resolve_output_dir(output, cli_config["CommandName"], config_path)

    if debug:
        logger.debug(f"Output directory (resolved): {output_path}")

    # Resolve OpenAPI spec path: --api option, else config Api, else none
    api_path: Path | None = None
    if api:
        api_path = Path(api)
    elif cli_config.get("Api"):
        # Resolve relative to config file directory
        spec_path = Path(cli_config["Api"])
        if not spec_path.is_absolute():
            spec_path = config_dir / spec_path
        if spec_path.exists():
            api_path = spec_path
        else:
            click.secho(
                f"⚠️  Api '{cli_config['Api']}' not found, "
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
        raise SystemExit(1) from e

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
    generator = CliGenerator(config=cli_config, config_dir=config_dir)
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
        for group in groups.values():
            click.secho(f"     • {group.cli_name}", fg="yellow", nl=False)
            click.echo(f" ({len(group.operations)} commands)")
    else:
        click.secho("  🔧 Commands: ", fg="white", nl=False)
        click.echo("config only (no API commands)")

    click.echo()
    click.secho("📋 Validate:", fg="cyan", bold=True)
    click.echo(f"   pip install -e {output_path}")
    click.echo(f"   {cli_name} --help")


def resolve_output_dir(
    output: str | None, command_name: str, config_path: Path | None
) -> Path:
    """Return the directory to write the project to.

    Without an explicit ``--output`` it is a directory named after
    ``CommandName`` next to the configuration file, the layout ``bootstrap``
    produces and ``examples/`` uses, or in the current directory when there is
    no configuration file. The output directory is deleted before generation,
    so one that contains the configuration file is refused rather than
    destroying the file that describes the project.
    """
    base_dir = config_path.parent if config_path else Path.cwd()
    output_path = Path(output) if output else base_dir / command_name
    if config_path and (
        output_path == config_path.parent or output_path in config_path.parents
    ):
        click.secho(
            f"✗ Output directory '{output_path}' contains the configuration "
            f"file '{config_path}'. Choose a different --output.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)
    return output_path


def _load_cli_config(
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
            click.secho(f"✗ Could not load config file: {e}", fg="red", err=True)
            raise SystemExit(1) from e
    raw_config.update(overrides or {})

    # Validate with Pydantic schema
    try:
        validated = Config(**raw_config)
        config = validated.model_dump()
    except ValidationError as e:
        click.secho("✗ Invalid configuration:", fg="red", err=True)
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            click.secho(f"  • {field}: {error['msg']}", fg="red", err=True)
        raise SystemExit(1) from e

    # Expand #[Param] references
    try:
        return _expand_config_references(config)
    except ValueError as e:
        click.secho("✗ Invalid configuration:", fg="red", err=True)
        click.secho(f"  • {e}", fg="red", err=True)
        raise SystemExit(1) from e


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
