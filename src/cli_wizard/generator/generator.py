# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""CLI code generator using Jinja2 templates."""

import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader

from cli_wizard.generator.models import CommandGroup, Operation


def _build_url_path(op: Operation) -> str:
    """Build URL path with Python variable substitutions."""
    path = op.path
    for param in op.parameters:
        if param.location == "path":
            path = path.replace(f"{{{param.name}}}", f"{{{param.python_name}}}")
    return path


class CliGenerator:
    """Generates Click CLI code from parsed OpenAPI."""

    def __init__(
        self, config: dict[str, Any] | None = None, config_dir: Path | None = None
    ) -> None:
        """Initialize generator with package templates."""
        self.config = config or {}
        self.config_dir = config_dir or Path.cwd()
        self.env = Environment(
            loader=PackageLoader("cli_wizard", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["url_path"] = _build_url_path

    def generate(
        self,
        groups: dict[str, CommandGroup],
        output_dir: Path,
        cli_name: str,
        package_name: str,
    ) -> None:
        """Generate a complete CLI project."""
        self.package_name = package_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create project structure
        src_dir = output_dir / "src" / package_name
        commands_dir = src_dir / "commands"
        resources_dir = src_dir / "resources"
        commands_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Copy resources (e.g., CA file, splash file)
        ca_file_name = self._copy_ca_file(resources_dir)
        splash_file_name = self._copy_splash_file(resources_dir)

        # Compute main_dir with variable substitution
        main_dir = self._compute_main_dir(package_name)

        # Generate project files
        self._generate_pyproject(output_dir, cli_name, package_name)
        self._generate_readme(output_dir, cli_name)
        self._generate_version(output_dir)

        # Generate package files
        self._generate_package_init(src_dir, package_name)
        self._generate_cli_main(src_dir, package_name, groups)
        self._generate_client(src_dir)
        self._generate_logging(src_dir)
        self._generate_profile(src_dir)
        self._generate_constants(src_dir, ca_file_name, splash_file_name, main_dir)

        # Generate commands
        self._generate_commands_init(commands_dir, groups)
        self._generate_config_commands(commands_dir)
        for tag, group in groups.items():
            self._generate_command_group(group, commands_dir)

    def _generate_pyproject(
        self, output_dir: Path, cli_name: str, package_name: str
    ) -> None:
        """Generate pyproject.toml."""
        template = self.env.get_template("pyproject.toml.j2")
        content = template.render(
            cli_name=cli_name,
            package_name=package_name,
            config=self.config,
        )
        with open(output_dir / "pyproject.toml", "w") as f:
            f.write(content)

    def _generate_readme(self, output_dir: Path, cli_name: str) -> None:
        """Generate README.md."""
        template = self.env.get_template("README.md.j2")
        content = template.render(cli_name=cli_name, config=self.config)
        with open(output_dir / "README.md", "w") as f:
            f.write(content)

    def _generate_version(self, output_dir: Path) -> None:
        """Generate VERSION file."""
        version = self.config.get("version", "0.1.0")
        with open(output_dir / "VERSION", "w") as f:
            f.write(f"{version}\n")

    def _generate_package_init(self, src_dir: Path, package_name: str) -> None:
        """Generate package __init__.py."""
        template = self.env.get_template("package_init.py.j2")
        content = template.render(package_name=package_name)
        with open(src_dir / "__init__.py", "w") as f:
            f.write(content)

    def _generate_cli_main(
        self, src_dir: Path, package_name: str, groups: dict[str, CommandGroup]
    ) -> None:
        """Generate main CLI entry point."""
        template = self.env.get_template("cli.py.j2")
        content = template.render(
            package_name=package_name,
            groups=groups,
            config=self.config,
        )
        with open(src_dir / "cli.py", "w") as f:
            f.write(content)

    def _generate_client(self, src_dir: Path) -> None:
        """Generate API client module."""
        template = self.env.get_template("client.py.j2")
        content = template.render(config=self.config)
        with open(src_dir / "client.py", "w") as f:
            f.write(content)

    def _generate_logging(self, src_dir: Path) -> None:
        """Generate logging module."""
        template = self.env.get_template("logging.py.j2")
        content = template.render(config=self.config)
        with open(src_dir / "logging.py", "w") as f:
            f.write(content)

    def _generate_profile(self, src_dir: Path) -> None:
        """Generate profile module."""
        template = self.env.get_template("profile.py.j2")
        content = template.render(config=self.config)
        with open(src_dir / "profile.py", "w") as f:
            f.write(content)

    def _generate_constants(
        self,
        src_dir: Path,
        ca_file_name: str | None,
        splash_file_name: str | None,
        main_dir: str,
    ) -> None:
        """Generate constants module."""
        template = self.env.get_template("constants.py.j2")
        content = template.render(
            config=self.config,
            ca_file_name=ca_file_name,
            splash_file_name=splash_file_name,
            main_dir=main_dir,
        )
        with open(src_dir / "constants.py", "w") as f:
            f.write(content)

    def _copy_ca_file(self, resources_dir: Path) -> str | None:
        """Copy CA file to resources directory if specified in config."""
        ca_file = self.config.get("CaFile")
        if not ca_file:
            return None

        # Resolve CA file path relative to config directory
        ca_path = Path(ca_file)
        if not ca_path.is_absolute():
            ca_path = self.config_dir / ca_file

        if not ca_path.exists():
            return None

        # Copy to resources directory with original filename
        dest_path = resources_dir / ca_path.name
        shutil.copy2(ca_path, dest_path)
        return ca_path.name

    def _compute_main_dir(self, package_name: str) -> str:
        """Get main directory path from config.

        The #[Param] references should already be resolved by config loader.
        ${VAR} environment variables are kept as-is for runtime expansion.
        """
        main_dir = self.config.get("MainDir")
        if main_dir is not None:
            return str(main_dir)
        return f"${{HOME}}/.{package_name}"

    def _copy_splash_file(self, resources_dir: Path) -> str | None:
        """Copy splash file to resources directory if specified in config."""
        splash_file = self.config.get("SplashFile")
        if not splash_file:
            return None

        # Resolve splash file path relative to config directory
        splash_path = Path(splash_file)
        if not splash_path.is_absolute():
            splash_path = self.config_dir / splash_file

        if not splash_path.exists():
            return None

        # Copy to resources directory with original filename
        dest_path = resources_dir / splash_path.name
        shutil.copy2(splash_path, dest_path)
        return splash_path.name

    def _generate_commands_init(
        self, commands_dir: Path, groups: dict[str, CommandGroup]
    ) -> None:
        """Generate commands __init__.py."""
        template = self.env.get_template("commands_init.py.j2")
        content = template.render(groups=groups)
        with open(commands_dir / "__init__.py", "w") as f:
            f.write(content)

    def _generate_config_commands(self, commands_dir: Path) -> None:
        """Generate config commands module."""
        template = self.env.get_template("commands_config.py.j2")
        content = template.render(package_name=self.package_name, config=self.config)
        with open(commands_dir / "config.py", "w") as f:
            f.write(content)

    def _generate_command_group(self, group: CommandGroup, commands_dir: Path) -> None:
        """Generate a command group file."""
        template = self.env.get_template("command_group.py.j2")
        content = template.render(
            group=group, config=self.config, package_name=self.package_name
        )
        with open(commands_dir / f"{group.module_name}.py", "w") as f:
            f.write(content)
