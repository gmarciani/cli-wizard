# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Bootstrap command for CLI Wizard."""

import getpass
import logging
from datetime import date
from pathlib import Path
from typing import Any

import click
import yaml
from jinja2 import Environment, PackageLoader

from cli_wizard.commands.common import emit_json
from cli_wizard.commands.generate import resolve_output_dir
from cli_wizard.config.project import load_cli_config
from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.errors import Aborted
from cli_wizard.generator import CliGenerator

logger = logging.getLogger(__name__)


# Width beyond which PyYAML would wrap a scalar onto a second line
YAML_NO_WRAP_WIDTH = 2**31 - 1


# Parameters prompted during bootstrap (in order)
BOOTSTRAP_PARAMS: list[str] = [
    "CommandName",
    "ProjectName",
    "PackageName",
    "Description",
    "AuthorName",
    "AuthorEmail",
    "PythonVersion",
    "GithubUser",
    "Version",
    "CopyrightYear",
    "RepositoryUrl",
    "HomePageUrl",
]


def _get_default_for_param(param_name: str, values: dict[str, Any]) -> str:
    """Get the default value for a parameter.

    Priority:
    1. Derived value based on other parameters (for CommandName, ProjectName, etc.)
    2. Schema default
    """
    if param_name == "CommandName":
        # Default to folder name in kebab-case
        target_dir_name = str(values.get("_target_dir_name", "my-project"))
        return target_dir_name.lower().replace("_", "-").replace(" ", "-")

    if param_name == "ProjectName":
        # Default to title case of CommandName
        command_name = str(values.get("CommandName", "my-project"))
        words = command_name.replace("-", " ").replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    if param_name == "PackageName":
        # Default to snake_case of CommandName
        command_name = str(values.get("CommandName", "my-project"))
        return command_name.lower().replace("-", "_").replace(" ", "_")

    if param_name == "GithubUser":
        # Default to current system username
        return getpass.getuser()

    if param_name == "CopyrightYear":
        # Default to current year
        return str(date.today().year)

    if param_name == "RepositoryUrl":
        # Default to GitHub URL based on GithubUser and CommandName
        github_user = str(values.get("GithubUser", "username"))
        command_name = str(values.get("CommandName", "my-project"))
        return f"https://github.com/{github_user}/{command_name}"

    if param_name == "HomePageUrl":
        # Default to the repository, which is prompted just before this one
        return str(values.get("RepositoryUrl", ""))

    # Use schema default
    default_value = Config.get_field_default(param_name)
    return str(default_value) if default_value is not None else ""


@click.command(
    help="""Bootstrap a new CLI project.

You will be guided through a step by step procedure to generate
a basic CLI and an extensible configuration file to evolve it.
No OpenAPI file is required. An existing configuration file is
overwritten, after confirmation, without keeping any of its values.

The project is written to the --output directory, by default a directory named
after CommandName next to the configuration file."""
)
@click.option(
    "--configuration",
    "-c",
    type=click.Path(dir_okay=False, resolve_path=True),
    default=None,
    help=f"Path for {CONFIG_FILE_NAME} (default: ./{CONFIG_FILE_NAME})",
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
    help="Skip the confirmation prompts to overwrite an existing configuration "
    "file or to write into a non-empty directory",
)
@click.pass_context
def bootstrap(
    ctx: click.Context, configuration: str | None, output: str | None, force: bool
) -> None:
    """Bootstrap command implementation."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    # Determine where to write config file
    if configuration:
        config_path = Path(configuration)
    else:
        config_path = Path.cwd() / CONFIG_FILE_NAME

    if debug:
        logger.debug(f"Config path: {config_path}")
        logger.debug(f"Output directory (CLI): {output}")
        logger.debug(f"Force mode: {force}")

    # Confirm before anything is prompted or written: an existing config is
    # replaced, none of its values kept
    if config_path.exists() and not force:
        click.secho(
            f"⚠️  Configuration file '{config_path}' already exists.",
            fg="yellow",
            err=True,
        )
        if not click.confirm("Do you want to overwrite it?", err=True):
            raise Aborted()

    # Gather project information interactively, on stderr: stdout holds the
    # one JSON result
    click.secho("\n📋 Project Configuration\n", fg="cyan", bold=True, err=True)

    # Collect values for bootstrap parameters. CommandName defaults to the
    # name of the output directory when one is given, else to the name of the
    # directory the configuration file lives in.
    target_dir_name = Path(output).name if output else config_path.parent.name
    values: dict = {"_target_dir_name": target_dir_name}

    for param_name in BOOTSTRAP_PARAMS:
        description = Config.get_field_description(param_name)
        default = _get_default_for_param(param_name, values)

        value = click.prompt(
            description,
            default=default,
            err=True,
        )
        values[param_name] = value

    # Remove internal keys
    del values["_target_dir_name"]

    cli_config = values

    # Derive additional values if not already set
    if "MainDir" not in cli_config:
        cli_config["MainDir"] = f"${{HOME}}/.{cli_config['CommandName']}"
    if "ProfileFile" not in cli_config:
        cli_config["ProfileFile"] = "#[MainDir]/profiles.yaml"

    if debug:
        logger.debug(f"Config: {cli_config}")

    target_dir = resolve_output_dir(output, cli_config["CommandName"], config_path)

    if debug:
        logger.debug(f"Output directory (resolved): {target_dir}")

    # Check if directory exists and is not empty
    if target_dir.exists():
        contents = list(target_dir.iterdir())
        if contents and not force:
            click.secho(
                f"⚠️  Directory '{target_dir}' already exists and is not empty.",
                fg="yellow",
                err=True,
            )
            if not click.confirm("Do you want to continue anyway?", err=True):
                raise Aborted()

    # Generate config file
    click.echo(err=True)
    click.secho("📄 Writing configuration file...", fg="cyan", err=True)
    _generate_config_file(config_path, cli_config)
    click.secho(f"   ✓ {config_path}", fg="green", err=True)

    # Load the generated config file (validates with Pydantic and expands references)
    cli_config = load_cli_config(config_path)

    # Generate CLI project using the same generator as 'generate' command
    click.echo(err=True)
    click.secho("⚙️  Generating CLI project...", fg="cyan", err=True)

    cli_name = cli_config["CommandName"]
    package_name = cli_config["PackageName"]

    generator = CliGenerator(config=cli_config, config_dir=config_path.parent)
    generator.generate({}, target_dir, cli_name, package_name)

    # Progress and hints go to stderr; stdout holds the one JSON result
    click.secho(
        f"\n✓ Project '{cli_config['ProjectName']}' bootstrapped successfully!",
        fg="green",
        bold=True,
        err=True,
    )
    click.secho("📋 Validate:", fg="cyan", bold=True, err=True)
    click.echo(f"   pip install -e {target_dir}", err=True)
    click.echo(f"   {cli_name} --help", err=True)

    next_command = f"cli-wizard generate --configuration {config_path}"
    if output:
        next_command += f" --output {target_dir}"
    click.echo(err=True)
    click.secho("📋 Next steps:", fg="cyan", bold=True, err=True)
    click.echo(f"   Customize {config_path}", err=True)
    click.echo(f"   {next_command}", err=True)

    summary = {
        "projectName": cli_config["ProjectName"],
        "cliName": cli_name,
        "packageName": package_name,
        "output": str(target_dir),
        "configuration": str(config_path),
        "nextCommand": next_command,
    }
    emit_json(summary)


def _yaml_value(value: Any) -> str:
    """Format a Python value as YAML."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        # Always double-quoted, and escaped by PyYAML rather than by hand, so
        # that quotes, backslashes and control characters survive the round
        # trip through the file. The template writes one value per line, so
        # line wrapping is disabled.
        return yaml.safe_dump(
            value,
            default_style='"',
            default_flow_style=True,
            allow_unicode=True,
            width=YAML_NO_WRAP_WIDTH,
        ).strip()
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(_yaml_value(v) for v in value) + "]"
    elif isinstance(value, dict):
        if not value:
            return "{}"
        return "{" + ", ".join(f"{k}: {_yaml_value(v)}" for k, v in value.items()) + "}"
    return str(value)


def _generate_config_file(config_path: Path, config: dict) -> None:
    """Generate the cli-wizard.yaml configuration file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(  # noqa: S701 - renders Python and YAML, not HTML
        loader=PackageLoader("cli_wizard", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["yaml_value"] = _yaml_value

    # Build context for template
    context = {
        **config,
        "config": config,
        "CopyrightYear": date.today().year,
        "_schema_fields": Config.get_all_fields_metadata(),
        "_prompted_params": set(BOOTSTRAP_PARAMS),
        "_values": config,
    }

    template = env.get_template("cli-wizard.yaml.j2")
    content = template.render(**context)
    config_path.write_text(content)
