# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""Bootstrap command for CLI Wizard."""

import getpass
import logging
import os
from pathlib import Path
from datetime import date
from typing import Any

import click
import yaml
from jinja2 import Environment, PackageLoader, BaseLoader

from cli_wizard.config.schema import Config
from cli_wizard.constants import CONFIG_FILE_NAME

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
    else:
        # Create the directory
        target_dir.mkdir(parents=True, exist_ok=True)
        click.secho(f"📁 Created directory: {target_dir}", fg="cyan")

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

    # Derive additional values
    values["RepositoryUrl"] = (
        f"https://github.com/{values['GithubUser']}/{values['CommandName']}"
    )
    values["MainDir"] = f"${{HOME}}/.{values['CommandName']}"
    values["ProfileFile"] = f"{values['MainDir']}/profiles.yaml"
    values["LogFile"] = f"{values['MainDir']}/{values['CommandName']}.log"
    values["CopyrightYear"] = date.today().year

    # Remove internal keys
    del values["_target_dir_name"]

    # Add schema metadata for config template generation
    values["_schema_fields"] = Config.get_all_fields_metadata()
    values["_prompted_params"] = set(BOOTSTRAP_PARAMS)
    # Pass all values for template lookup
    values["_values"] = {k: v for k, v in values.items() if not k.startswith("_")}

    if debug:
        logger.debug(f"Template context: {values}")

    # Generate project files
    click.echo()
    click.secho("⚙️  Generating project files...", fg="cyan")

    _generate_project(target_dir, values, config_path)

    # Summary
    click.secho(
        f"\n✓ Project '{values['ProjectName']}' bootstrapped successfully!",
        fg="green",
        bold=True,
    )
    click.secho("  📁 Location: ", fg="white", nl=False)
    click.echo(target_dir)
    click.secho("  📄 Config: ", fg="white", nl=False)
    click.echo(config_path)

    click.echo()
    click.secho("📋 Next steps:", fg="cyan", bold=True)
    click.echo(f"   pip install -e {target_dir}")
    click.echo(f"   {values['CommandName']} --help")


def _get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    import cli_wizard

    package_dir = Path(cli_wizard.__file__).parent
    return package_dir / "templates"


def _discover_templates(templates_dir: Path) -> list[tuple[Path, str, bool]]:
    """Discover all files in the templates directory.

    Returns a list of tuples: (file_path_relative_to_templates, output_filename, is_template)
    - is_template: True if file has .j2 extension (content should be rendered)
    """
    # Templates that require OpenAPI-specific variables (skip for bootstrap)
    skip_templates = {
        "group.py.j2",  # Requires 'group' variable from OpenAPI parsing
    }

    files = []
    for file_path in templates_dir.rglob("*"):
        if file_path.is_file():
            # Skip templates that require OpenAPI-specific variables
            if file_path.name in skip_templates:
                continue

            # Get path relative to templates_dir
            rel_path = file_path.relative_to(templates_dir)
            # Check if it's a Jinja2 template
            is_template = file_path.suffix == ".j2"
            # Remove .j2 extension for output filename if it's a template
            output_name = str(rel_path)[:-3] if is_template else str(rel_path)
            files.append((rel_path, output_name, is_template))
    return files


def _resolve_output_path(output_name: str, context: dict) -> str:
    """Resolve output path by expanding Jinja2 variables.

    Handles Jinja2 variables in path (e.g., {{ PackageName }}).
    """
    # Use Jinja2 to expand variables in the path
    env = Environment(loader=BaseLoader())
    template = env.from_string(output_name)
    resolved = template.render(**context)
    return resolved


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


def _generate_project(target_dir: Path, context: dict, config_path: Path) -> None:
    """Generate all project files by discovering and rendering templates.

    Args:
        target_dir: Directory where project files are generated
        context: Template context with all variables
        config_path: Path where config file should be written
    """
    templates_dir = _get_templates_dir()
    files = _discover_templates(templates_dir)

    env = Environment(
        loader=PackageLoader("cli_wizard", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["yaml_value"] = _yaml_value

    # Add 'groups' for templates that expect it (empty for bootstrap)
    context["groups"] = {}

    for file_rel_path, output_name, is_template in sorted(files):
        # Resolve output path (expand Jinja2 variables)
        resolved_output = _resolve_output_path(output_name, context)

        # Handle config file separately - write to config_path instead of target_dir
        if resolved_output == CONFIG_FILE_NAME:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            template_name = str(file_rel_path).replace(os.sep, "/")
            template = env.get_template(template_name)
            content = template.render(**context)
            config_path.write_text(content)
            click.secho(f"   ✓ {config_path}", fg="green")
            continue

        # Create output directory if needed
        output_path = target_dir / resolved_output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if is_template:
            # Render Jinja2 template
            template_name = str(file_rel_path).replace(os.sep, "/")
            template = env.get_template(template_name)
            content = template.render(**context)
            output_path.write_text(content)
        else:
            # Copy file as-is (but path is still expanded)
            source_path = templates_dir / file_rel_path
            output_path.write_bytes(source_path.read_bytes())

        click.secho(f"   ✓ {resolved_output}", fg="green")
