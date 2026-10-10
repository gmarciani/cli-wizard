# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Generate command for CLI Wizard."""

import logging
import shutil
from pathlib import Path

import click

from cli_wizard.commands.common import emit_json
from cli_wizard.config.project import load_cli_config
from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.errors import Aborted, OutputDirError
from cli_wizard.generator import CliGenerator, OpenApiParser
from cli_wizard.generator.generator import resolve_ruff

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
    cli_config = load_cli_config(config_path, overrides)

    # Resolve OpenAPI spec path: --api option, else config Api, else none
    api_path: Path | None = None
    if api:
        api_path = Path(api)
    elif cli_config.get("Api"):
        spec_path = _resolve_input(cli_config["Api"], config_dir)
        if spec_path.exists():
            api_path = spec_path
        else:
            click.secho(
                f"⚠️  Api '{cli_config['Api']}' not found, "
                "generating CLI without API commands",
                fg="yellow",
                err=True,
            )

    if debug:
        logger.debug(f"OpenAPI spec (resolved): {api_path}")

    # The output directory is deleted, so it must not hold any input
    inputs = {"OpenAPI spec": api_path}
    for key, label in (("CaFile", "CA file"), ("SplashFile", "splash file")):
        if cli_config.get(key):
            inputs[label] = _resolve_input(cli_config[key], config_dir)
    output_path = resolve_output_dir(
        output,
        cli_config["CommandName"],
        config_path,
        {label: path for label, path in inputs.items() if path and path.exists()},
    )

    if debug:
        logger.debug(f"Output directory (resolved): {output_path}")

    # Get CLI name and package name from config
    cli_name = cli_config["CommandName"]
    package_name = cli_config["PackageName"]

    # Parse OpenAPI spec if provided
    groups: dict = {}
    if api_path:
        click.secho("📄 Parsing OpenAPI spec: ", fg="cyan", nl=False, err=True)
        click.echo(api_path, err=True)
        parser = OpenApiParser(str(api_path))

        groups = parser.parse(
            exclude_tags=cli_config.get("ExcludeTags", []),
            include_tags=cli_config.get("IncludeTags", []),
            tag_mapping=cli_config.get("TagMapping", {}),
            include_operations=cli_config.get("IncludeOperations", []),
            exclude_operations=cli_config.get("ExcludeOperations", []),
        )

        if not groups:
            click.secho("⚠️  No operations found in OpenAPI spec", fg="yellow", err=True)
    else:
        click.secho(
            "ℹ️  No OpenAPI spec provided, generating CLI without API commands",
            fg="cyan",
            err=True,
        )

    # Verify the formatter and the resource files before deleting the output
    resolve_ruff()
    generator = CliGenerator(config=cli_config, config_dir=config_dir)
    generator.check_resources()

    # Clean up output directory before generating
    if output_path.exists():
        # Check if we're inside the output directory
        try:
            cwd: Path | None = Path.cwd()
        except OSError:
            # Current directory may already be deleted
            cwd = None
        if cwd is not None and (output_path in cwd.parents or output_path == cwd):
            raise OutputDirError(
                "Cannot clean output directory while inside it. "
                "Please run from a different directory."
            )

        # Confirm before destroying a directory that holds work
        if not force and any(output_path.iterdir()):
            if not click.confirm(
                f"⚠️  Output directory '{output_path}' is not empty. "
                "Its entire contents will be deleted. Continue?",
                err=True,
            ):
                raise Aborted()

        click.secho("🧹 Cleaning output directory: ", fg="cyan", nl=False, err=True)
        click.echo(output_path, err=True)
        shutil.rmtree(output_path)

    # Generate CLI project
    click.secho("⚙️  Generating CLI project: ", fg="cyan", nl=False, err=True)
    click.echo(output_path, err=True)
    generator.generate(groups, output_path, cli_name, package_name)

    # Progress and hints go to stderr; stdout holds the one JSON result
    click.secho(f"\n✓ Generated CLI '{cli_name}'", fg="green", bold=True, err=True)
    click.secho("📋 Validate:", fg="cyan", bold=True, err=True)
    click.echo(f"   pip install -e {output_path}", err=True)
    click.echo(f"   {cli_name} --help", err=True)

    summary = {
        "cliName": cli_name,
        "packageName": package_name,
        "output": str(output_path),
        "configuration": str(config_path) if config_path else None,
        "api": str(api_path) if api_path else None,
        "groups": [
            {"name": group.cli_name, "commands": len(group.operations)}
            for group in groups.values()
        ],
    }
    emit_json(summary)


def resolve_output_dir(
    output: str | None,
    command_name: str,
    config_path: Path | None,
    inputs: dict[str, Path] | None = None,
) -> Path:
    """Return the directory to write the project to.

    Without an explicit ``--output`` it is a directory named after
    ``CommandName`` next to the configuration file, the layout ``bootstrap``
    produces and ``examples/`` uses, or in the current directory when there is
    no configuration file. The output directory is deleted before generation,
    so one that contains the configuration file, or any of the other ``inputs``
    (a label for each file mapped to its path), is refused rather than
    destroying the files that describe the project.
    """
    base_dir = config_path.parent if config_path else Path.cwd()
    output_path = Path(output) if output else base_dir / command_name
    guarded = {"configuration file": config_path} if config_path else {}
    guarded.update(inputs or {})
    for label, path in guarded.items():
        resolved = path.resolve()
        if output_path.resolve() in resolved.parents:
            raise OutputDirError(
                f"Output directory '{output_path}' contains the {label} "
                f"'{resolved}'. Choose a different --output."
            )
    return output_path


def _resolve_input(value: str, config_dir: Path) -> Path:
    """Return the path of an input file, relative to the configuration file."""
    path = Path(value)
    return path if path.is_absolute() else config_dir / path
