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
            keep_trailing_newline=True,
        )
        self.env.filters["url_path"] = _build_url_path

    def _template_context(self, **extra: Any) -> dict[str, Any]:
        """Build template context with all config values spread at top level.

        This allows templates to use {{ ParamName }} directly instead of
        {{ config.ParamName }}.
        """
        context = {
            **self.config,  # Spread all config values at top level
            "config": self.config,  # Also include as nested dict for compatibility
            "cli_name": self.cli_name,
            "package_name": self.package_name,
        }
        context.update(extra)
        return context

    def generate(
        self,
        groups: dict[str, CommandGroup],
        output_dir: Path,
        cli_name: str,
        package_name: str,
    ) -> None:
        """Generate a complete CLI project."""
        self.package_name = package_name
        self.cli_name = cli_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create project structure
        src_dir = output_dir / "src" / package_name
        commands_dir = src_dir / "commands"
        resources_dir = src_dir / "resources"
        tests_dir = output_dir / "tests"

        commands_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Create .github directories only if needed
        github_dir = output_dir / ".github"
        workflows_dir = github_dir / "workflows"
        issue_template_dir = github_dir / "ISSUE_TEMPLATE"
        if self.config.get("IncludeGithubWorkflows", False):
            workflows_dir.mkdir(parents=True, exist_ok=True)
            issue_template_dir.mkdir(parents=True, exist_ok=True)

        # Copy resources (e.g., CA file, splash file)
        ca_file_name = self._copy_ca_file(resources_dir)
        splash_file_name = self._copy_splash_file(resources_dir)

        # Compute main_dir with variable substitution
        main_dir = self._compute_main_dir(package_name)

        # Generate root project files
        self._generate_pyproject(output_dir, cli_name, package_name)
        self._generate_readme(output_dir, cli_name)
        self._generate_version(output_dir)
        self._generate_gitignore(output_dir)
        self._generate_makefile(output_dir)
        self._generate_changelog(output_dir)
        self._generate_development(output_dir)
        self._generate_license(output_dir)
        self._generate_manifest(output_dir)
        self._generate_tox(output_dir)
        self._generate_precommit(output_dir)

        # Generate .github files (conditionally)
        if self.config.get("IncludeGithubWorkflows", False):
            self._generate_github_files(github_dir, workflows_dir, issue_template_dir)

        # Generate test files
        self._generate_tests(tests_dir)

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
        content = template.render(**self._template_context())
        with open(output_dir / "pyproject.toml", "w") as f:
            f.write(content)

    def _generate_readme(self, output_dir: Path, cli_name: str) -> None:
        """Generate README.md."""
        template = self.env.get_template("README.md.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "README.md", "w") as f:
            f.write(content)

    def _generate_version(self, output_dir: Path) -> None:
        """Generate VERSION file."""
        version = self.config.get("Version", "0.1.0")
        with open(output_dir / "VERSION", "w") as f:
            f.write(f"{version}\n")

    def _generate_package_init(self, src_dir: Path, package_name: str) -> None:
        """Generate package __init__.py."""
        template = self.env.get_template("src/{{ PackageName }}/__init__.py.j2")
        content = template.render(**self._template_context())
        with open(src_dir / "__init__.py", "w") as f:
            f.write(content)

    def _generate_cli_main(
        self, src_dir: Path, package_name: str, groups: dict[str, CommandGroup]
    ) -> None:
        """Generate main CLI entry point."""
        template = self.env.get_template("src/{{ PackageName }}/cli.py.j2")
        content = template.render(**self._template_context(groups=groups))
        with open(src_dir / "cli.py", "w") as f:
            f.write(content)

    def _generate_client(self, src_dir: Path) -> None:
        """Generate API client module."""
        template = self.env.get_template("src/{{ PackageName }}/client.py.j2")
        content = template.render(**self._template_context())
        with open(src_dir / "client.py", "w") as f:
            f.write(content)

    def _generate_logging(self, src_dir: Path) -> None:
        """Generate logging module."""
        template = self.env.get_template("src/{{ PackageName }}/logging.py.j2")
        content = template.render(**self._template_context())
        with open(src_dir / "logging.py", "w") as f:
            f.write(content)

    def _generate_profile(self, src_dir: Path) -> None:
        """Generate profile module."""
        template = self.env.get_template("src/{{ PackageName }}/profile.py.j2")
        content = template.render(**self._template_context())
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
        template = self.env.get_template("src/{{ PackageName }}/constants.py.j2")
        content = template.render(
            **self._template_context(
                ca_file_name=ca_file_name,
                splash_file_name=splash_file_name,
                main_dir=main_dir,
            )
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
        template = self.env.get_template(
            "src/{{ PackageName }}/commands/__init__.py.j2"
        )
        content = template.render(**self._template_context(groups=groups))
        with open(commands_dir / "__init__.py", "w") as f:
            f.write(content)

    def _generate_config_commands(self, commands_dir: Path) -> None:
        """Generate config commands module."""
        template = self.env.get_template("src/{{ PackageName }}/commands/config.py.j2")
        content = template.render(**self._template_context())
        with open(commands_dir / "config.py", "w") as f:
            f.write(content)

    def _generate_command_group(self, group: CommandGroup, commands_dir: Path) -> None:
        """Generate a command group file."""
        template = self.env.get_template("src/{{ PackageName }}/commands/group.py.j2")
        content = template.render(**self._template_context(group=group))
        with open(commands_dir / f"{group.module_name}.py", "w") as f:
            f.write(content)

    def _generate_gitignore(self, output_dir: Path) -> None:
        """Generate .gitignore."""
        template = self.env.get_template(".gitignore.j2")
        content = template.render(**self._template_context())
        with open(output_dir / ".gitignore", "w") as f:
            f.write(content)

    def _generate_makefile(self, output_dir: Path) -> None:
        """Generate Makefile."""
        template = self.env.get_template("Makefile.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "Makefile", "w") as f:
            f.write(content)

    def _generate_changelog(self, output_dir: Path) -> None:
        """Generate CHANGELOG.md."""
        template = self.env.get_template("CHANGELOG.md.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "CHANGELOG.md", "w") as f:
            f.write(content)

    def _generate_development(self, output_dir: Path) -> None:
        """Generate DEVELOPMENT.md."""
        template = self.env.get_template("DEVELOPMENT.md.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "DEVELOPMENT.md", "w") as f:
            f.write(content)

    def _generate_license(self, output_dir: Path) -> None:
        """Generate LICENSE."""
        template = self.env.get_template("LICENSE.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "LICENSE", "w") as f:
            f.write(content)

    def _generate_manifest(self, output_dir: Path) -> None:
        """Generate MANIFEST.in."""
        template = self.env.get_template("MANIFEST.in.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "MANIFEST.in", "w") as f:
            f.write(content)

    def _generate_tox(self, output_dir: Path) -> None:
        """Generate tox.ini."""
        template = self.env.get_template("tox.ini.j2")
        content = template.render(**self._template_context())
        with open(output_dir / "tox.ini", "w") as f:
            f.write(content)

    def _generate_precommit(self, output_dir: Path) -> None:
        """Generate .pre-commit-config.yaml."""
        template = self.env.get_template("pre-commit-config.yaml.j2")
        content = template.render(**self._template_context())
        with open(output_dir / ".pre-commit-config.yaml", "w") as f:
            f.write(content)

    def _generate_github_files(
        self, github_dir: Path, workflows_dir: Path, issue_template_dir: Path
    ) -> None:
        """Generate .github directory files."""
        # Generate templated files
        templated_files = [
            (".github/CODEOWNERS.j2", github_dir / "CODEOWNERS"),
            (".github/labels.yaml.j2", github_dir / "labels.yaml"),
            (
                ".github/ISSUE_TEMPLATE/bug-report.yml.j2",
                issue_template_dir / "bug-report.yml",
            ),
            (
                ".github/ISSUE_TEMPLATE/config.yml.j2",
                issue_template_dir / "config.yml",
            ),
            (
                ".github/ISSUE_TEMPLATE/feature-request.yml.j2",
                issue_template_dir / "feature-request.yml",
            ),
        ]
        for template_name, output_path in templated_files:
            template = self.env.get_template(template_name)
            content = template.render(**self._template_context())
            with open(output_path, "w") as f:
                f.write(content)

        # Copy static files (non-templated)
        static_files = [
            (".github/dependabot.yaml", github_dir / "dependabot.yaml"),
            (".github/labeler.yaml", github_dir / "labeler.yaml"),
            (
                ".github/PULL_REQUEST_TEMPLATE.md",
                github_dir / "PULL_REQUEST_TEMPLATE.md",
            ),
            (
                ".github/workflows/changelog-enforcer.yaml",
                workflows_dir / "changelog-enforcer.yaml",
            ),
            (".github/workflows/codeql.yaml", workflows_dir / "codeql.yaml"),
            (".github/workflows/docs.yaml", workflows_dir / "docs.yaml"),
            (".github/workflows/labeler.yaml", workflows_dir / "labeler.yaml"),
            (
                ".github/workflows/pr-validation.yaml",
                workflows_dir / "pr-validation.yaml",
            ),
            (".github/workflows/release.yaml", workflows_dir / "release.yaml"),
            (".github/workflows/sync-labels.yaml", workflows_dir / "sync-labels.yaml"),
            (".github/workflows/test.yaml", workflows_dir / "test.yaml"),
        ]
        for template_name, output_path in static_files:
            # Use get_template to read static files through Jinja loader
            loader = self.env.loader
            if loader is not None:
                source = loader.get_source(self.env, template_name)[0]
                with open(output_path, "w") as f:
                    f.write(source)

    def _generate_tests(self, tests_dir: Path) -> None:
        """Generate test files."""
        # Generate cli_test.py directly in tests/
        template = self.env.get_template("tests/{{ PackageName }}/cli_test.py.j2")
        content = template.render(**self._template_context())
        with open(tests_dir / "cli_test.py", "w") as f:
            f.write(content)
