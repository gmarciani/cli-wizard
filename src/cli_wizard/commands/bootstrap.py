# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Bootstrap command for CLI Wizard."""

import getpass
import logging
import re
from pathlib import Path
from datetime import date
from typing import Any

import click
import yaml
from jinja2 import Environment, PackageLoader
from pydantic import ValidationError

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME
from cli_wizard.generator import CliGenerator

logger = logging.getLogger(__name__)


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
]


def _get_default_for_param(
    param_name: str, values: dict, existing_config: dict | None = None
) -> str:
    """Get the default value for a parameter.

    Priority:
    1. Existing config file value (if config exists)
    2. Derived value based on other parameters (for CommandName, ProjectName, etc.)
    3. Schema default
    """
    # First, check existing config
    if existing_config and param_name in existing_config:
        return str(existing_config[param_name])

    if param_name == "CommandName":
        # Default to folder name in kebab-case
        return (
            values.get("_target_dir_name", "my-project")
            .lower()
            .replace("_", "-")
            .replace(" ", "-")
        )

    if param_name == "ProjectName":
        # Default to title case of CommandName
        command_name = values.get("CommandName", "my-project")
        return " ".join(
            word.capitalize()
            for word in command_name.replace("-", " ").replace("_", " ").split()
        )

    if param_name == "PackageName":
        # Default to snake_case of CommandName
        command_name = values.get("CommandName", "my-project")
        return command_name.lower().replace("-", "_").replace(" ", "_")

    if param_name == "GithubUser":
        # Default to current system username
        return getpass.getuser()

    if param_name == "CopyrightYear":
        # Default to current year
        return str(date.today().year)

    if param_name == "RepositoryUrl":
        # Default to GitHub URL based on GithubUser and CommandName
        github_user = values.get("GithubUser", "username")
        command_name = values.get("CommandName", "my-project")
        return f"https://github.com/{github_user}/{command_name}"

    # Use schema default
    return str(Config.get_field_default(param_name) or "")


def _load_existing_config(config_path: Path) -> dict | None:
    """Load existing config file if it exists.

    Returns None if file doesn't exist or can't be parsed.
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        logger.warning(f"Could not load existing config: {e}")
        return None


@click.command(
    help="""Bootstrap a new CLI project.

You will be guided through a step by step procedure to generate
a basic CLI and an extensible configuration file to evolve it.
No OpenAPI file is required.

PATH is the directory where the project will be created. It can be a relative or absolute path."""
)
@click.argument(
    "path",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt if directory exists and is not empty",
)
@click.option(
    "--configuration",
    "-c",
    type=click.Path(dir_okay=False, resolve_path=True),
    default=None,
    help=f"Path for {CONFIG_FILE_NAME} (default: ./{CONFIG_FILE_NAME})",
)
@click.pass_context
def bootstrap(
    ctx: click.Context, path: str, force: bool, configuration: str | None
) -> None:
    """Bootstrap command implementation."""
    debug = ctx.obj.get("debug", False) if ctx.obj else False
    target_dir = Path(path)

    # Determine where to write config file
    if configuration:
        config_path = Path(configuration)
    else:
        config_path = Path.cwd() / CONFIG_FILE_NAME

    if debug:
        logger.debug(f"Target directory: {target_dir}")
        logger.debug(f"Config path: {config_path}")
        logger.debug(f"Force mode: {force}")

    # Check if directory exists and is not empty
    if target_dir.exists():
        contents = list(target_dir.iterdir())
        if contents and not force:
            click.secho(
                f"⚠️  Directory '{target_dir}' already exists and is not empty.",
                fg="yellow",
            )
            if not click.confirm("Do you want to continue anyway?"):
                click.secho("Aborted.", fg="red")
                raise SystemExit(1)

    # Load existing config if available (for default values)
    existing_config = _load_existing_config(config_path)
    if existing_config:
        click.secho(f"📄 Using existing config: {config_path}", fg="cyan")

    # Gather project information interactively
    click.secho("\n📋 Project Configuration\n", fg="cyan", bold=True)

    # Collect values for bootstrap parameters
    values: dict = {"_target_dir_name": target_dir.name}

    for param_name in BOOTSTRAP_PARAMS:
        description = Config.get_field_description(param_name)
        default = _get_default_for_param(param_name, values, existing_config)

        value = click.prompt(
            description,
            default=default,
        )
        values[param_name] = value

    # Remove internal keys
    del values["_target_dir_name"]

    # Merge with existing config (prompted values override)
    if existing_config:
        cli_config = {**existing_config, **values}
    else:
        cli_config = values

    # Derive additional values if not already set
    if "MainDir" not in cli_config:
        cli_config["MainDir"] = f"${{HOME}}/.{cli_config['CommandName']}"
    if "ProfileFile" not in cli_config:
        cli_config["ProfileFile"] = f"#[MainDir]/profiles.yaml"

    if debug:
        logger.debug(f"Config: {cli_config}")

    # Generate config file
    click.echo()
    click.secho("📄 Writing configuration file...", fg="cyan")
    _generate_config_file(config_path, cli_config)
    click.secho(f"   ✓ {config_path}", fg="green")

    # Load the generated config file (validates with Pydantic and expands references)
    cli_config = _load_cli_config(config_path)

    # Generate CLI project using the same generator as 'generate' command
    click.echo()
    click.secho("⚙️  Generating CLI project...", fg="cyan")

    cli_name = cli_config["CommandName"]
    package_name = cli_config["PackageName"]

    generator = CliGenerator(config=cli_config, config_dir=config_path.parent)
    generator.generate({}, target_dir, cli_name, package_name)

    # Summary
    click.secho(
        f"\n✓ Project '{cli_config['ProjectName']}' bootstrapped successfully!",
        fg="green",
        bold=True,
    )
    click.secho("  📁 Location: ", fg="white", nl=False)
    click.echo(target_dir)
    click.secho("  📄 Config: ", fg="white", nl=False)
    click.echo(config_path)

    click.echo()
    click.secho("📋 Validate:", fg="cyan", bold=True)
    click.echo(f"   pip install -e {target_dir}")
    click.echo(f"   {cli_name} --help")

    click.echo()
    click.secho("📋 Next steps:", fg="cyan", bold=True)
    click.echo(f"   Customize {config_path}")
    click.echo(f"   cli-wizard generate --configuration {config_path} {target_dir}")


def _yaml_value(value: Any) -> str:
    """Format a Python value as YAML."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        # Quote strings that might be ambiguous
        if value == "" or value in ("true", "false", "null", "yes", "no"):
            return f'"{value}"'
        # Quote strings with special characters
        if any(c in value for c in ":#{}[]&*!|>'\"%@`"):
            return f'"{value}"'
        return f'"{value}"'
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

    env = Environment(
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
    """Expand #[Param] references in config values recursively."""

    def expand_value(value: Any, config: dict[str, Any]) -> Any:
        if isinstance(value, str):
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

    expanded: dict[str, Any] = expand_value(config, config)
    return expand_value(expanded, expanded)
