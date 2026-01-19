# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""CLI code generator using Jinja2 templates."""

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

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize generator with package templates."""
        self.config = config or {}
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
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create project structure
        src_dir = output_dir / "src" / package_name
        commands_dir = src_dir / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        # Generate project files
        self._generate_pyproject(output_dir, cli_name, package_name)
        self._generate_readme(output_dir, cli_name)

        # Generate package files
        self._generate_package_init(src_dir, package_name)
        self._generate_cli_main(src_dir, package_name, groups)
        self._generate_client(src_dir)
        self._generate_constants(src_dir)

        # Generate commands
        self._generate_commands_init(commands_dir, groups)
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

    def _generate_constants(self, src_dir: Path) -> None:
        """Generate constants module."""
        template = self.env.get_template("constants.py.j2")
        content = template.render(config=self.config)
        with open(src_dir / "constants.py", "w") as f:
            f.write(content)

    def _generate_commands_init(
        self, commands_dir: Path, groups: dict[str, CommandGroup]
    ) -> None:
        """Generate commands __init__.py."""
        template = self.env.get_template("commands_init.py.j2")
        content = template.render(groups=groups)
        with open(commands_dir / "__init__.py", "w") as f:
            f.write(content)

    def _generate_command_group(self, group: CommandGroup, commands_dir: Path) -> None:
        """Generate a command group file."""
        template = self.env.get_template("command_group.py.j2")
        content = template.render(group=group, config=self.config)
        with open(commands_dir / f"{group.module_name}.py", "w") as f:
            f.write(content)
