# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Bootstrap command for CLI Wizard."""

import getpass
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import click
import yaml
from jinja2 import Environment, PackageLoader
from pydantic import ValidationError

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME
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


def _get_default_for_param(
    param_name: str,
    values: dict[str, Any],
    existing_config: dict[str, Any] | None = None,
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


def _load_existing_config(config_path: Path) -> dict[str, Any] | None:
    """Load existing config file if it exists.

    Returns None if file doesn't exist or can't be parsed.
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            result = yaml.safe_load(f)
            if result is None:
                return {}
            return dict(result)
    except (yaml.YAMLError, IOError) as e:
        logger.warning(f"Could not load existing config: {e}")
        return None


@click.command(
    help="""Bootstrap a new CLI project.

You will be guided through a step by step procedure to generate
a basic CLI and an extensible configuration file to evolve it.
No OpenAPI file is required.

PATH is the directory where the project will be created.
It can be a relative or absolute path."""
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
        cli_config["ProfileFile"] = "#[MainDir]/profiles.yaml"

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
