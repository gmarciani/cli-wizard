# Copyright (c) 2026, Giacomo Marciani
# Licensed under the MIT License

"""CLI code generator using Jinja2 templates."""

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Environment, PackageLoader

from cli_wizard.config.schema import Config, python_versions_from
from cli_wizard.generator.models import (
    CommandGroup,
    Operation,
    Parameter,
    RequestBodyProperty,
)

_PLACEHOLDER_PATTERN = re.compile(r"\{([^{}]*)\}")


def _build_url_expression(op: Operation) -> str:
    """Build the request path as a Python expression, quotes included.

    An operation with `in: path` parameters becomes an f-string that
    interpolates the matching command options, each percent-encoded so a
    value such as `a@b.com` cannot alter the URL structure. Paths with no
    such parameter stay plain string literals, and a placeholder no
    parameter declares is escaped so it survives as a literal instead of
    being evaluated.
    """
    by_name = {param.name: param for param in op.path_parameters}
    if not by_name:
        return f'"{op.path}"'

    def substitute(match: re.Match[str]) -> str:
        param = by_name.get(match.group(1))
        if param is None:
            return f"{{{{{match.group(1)}}}}}"
        return f"{{encode_path_param({param.python_name})}}"

    return f'f"{_PLACEHOLDER_PATTERN.sub(substitute, op.path)}"'


# One sample per Click type, fed to the generated commands by the generated
# tests. A path string needs percent-encoding so the test proves the URL is
# escaped rather than interpolated raw.
_SAMPLE_VALUES: dict[str, Any] = {"str": "test", "int": 1, "float": 1.5, "bool": True}
_SAMPLE_PATH_STRING = "a@b.com"


def _sample_value(spec_field: Parameter | RequestBodyProperty) -> Any:
    """Pick a value of the right type for one command option."""
    enum: list[str] = getattr(spec_field, "enum", [])
    return enum[0] if enum else _SAMPLE_VALUES[spec_field.click_type]


def _operation_test_case(op: Operation) -> dict[str, Any]:
    """Describe the request one generated command must make.

    Everything the generator already knows at render time - the option names,
    the resolved URL, the query and body shapes with their JSON types - so the
    generated suite asserts the spec-derived surface rather than the
    scaffolding that is identical for every user.
    """
    argv: list[str] = []
    encoded: dict[str, str] = {}
    params: dict[str, Any] = {}
    body: dict[str, Any] = {}

    for param in op.path_parameters:
        is_string = param.click_type == "str"
        value = _SAMPLE_PATH_STRING if is_string else _sample_value(param)
        encoded[param.name] = quote(str(value), safe="")
        argv += [f"--{param.cli_name}", str(value)]
    for param in op.query_parameters:
        value = _sample_value(param)
        params[param.name] = [value] if param.is_array else value
        argv += [f"--{param.cli_name}", str(value)]
    for prop in op.body_properties:
        value = _sample_value(prop)
        body[prop.name] = [value] if prop.is_array else value
        argv.append(f"--{prop.cli_name}")
        # A boolean property is a flag, unless it repeats as an array
        if prop.click_type != "bool" or prop.is_array:
            argv.append(str(value))

    return {
        "argv": argv,
        "path": _PLACEHOLDER_PATTERN.sub(
            lambda match: encoded.get(match.group(1), match.group(0)), op.path
        ),
        "params": params or None,
        # The command sends no body on a GET, whatever the spec declares.
        "body": body or None if op.method != "GET" else None,
    }


def _sensitive_field_names(groups: dict[str, CommandGroup]) -> list[str]:
    """Collect the wire names the spec marks as credentials.

    Baked into the generated redaction module as one project-wide set, so
    nothing has to be threaded through the client and every command. A
    field that is a credential in one operation is one everywhere.
    """
    names = set()
    for group in groups.values():
        for op in group.operations:
            spec_fields: list[Parameter | RequestBodyProperty] = [
                *op.parameters,
                *op.body_properties,
            ]
            for spec_field in spec_fields:
                if spec_field.spec_format == "password" or spec_field.write_only:
                    names.add(spec_field.name)
    return sorted(names)


logger = logging.getLogger(__name__)


# Ruff invocations applied to generated code, as (args...) without the binary
# or the target path. The generated tox.ini [testenv:format] must run the same
# commands; test_format_recipe_matches_tox_template enforces that.
RUFF_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("check", "--fix"),
    ("format",),
)


class RuffNotFoundError(RuntimeError):
    """Raised when the ruff formatter cannot be located."""


def resolve_ruff() -> list[str]:
    """Return the command prefix used to invoke ruff.

    cli-wizard depends on ruff, so the copy installed alongside it is tried
    first. That copy has the pinned version, while a ruff found on PATH could
    be any version and would format differently - the exact instability this
    formatting step exists to prevent. PATH is only a fallback for unusual
    installations.
    """
    probe = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        capture_output=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "ruff"]

    ruff_path = shutil.which("ruff")
    if ruff_path:
        return [ruff_path]

    raise RuffNotFoundError(
        "ruff is required to generate formatter-stable code but could not be "
        "run. It is a dependency of cli-wizard, so this usually means the "
        "installation is broken; reinstalling cli-wizard should fix it."
    )


class CliGenerator:
    """Generates Click CLI code from parsed OpenAPI."""

    # Config fields that become runtime profile parameters in the generated CLI.
    # Maps wizard config PascalCase names to camelCase profile key names.
    PROFILE_PARAM_FIELDS: dict[str, str] = {
        "DefaultBaseUrl": "baseUrl",
        "Timeout": "timeout",
        "OutputFormat": "outputFormat",
        "OutputColors": "outputColors",
        "JsonIndent": "jsonIndent",
        "TableStyle": "tableStyle",
        "LogLevel": "logLevel",
        "RetryMaxAttempts": "retryMaxAttempts",
        "RetryBackoffFactor": "retryBackoffFactor",
    }

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
        self.env.filters["url_expression"] = _build_url_expression
        self.env.filters["test_case"] = _operation_test_case

    def _template_context(self, **extra: Any) -> dict[str, Any]:
        """Build template context with all config values spread at top level.

        This allows templates to use {{ ParamName }} directly instead of
        {{ config.ParamName }}.
        """
        # Build profile defaults from config
        profile_defaults = {
            profile_key: self.config[config_key]
            for config_key, profile_key in self.PROFILE_PARAM_FIELDS.items()
            if config_key in self.config
        }
        # Runtime-only profile parameters (not derived from wizard config)
        profile_defaults["accessToken"] = None

        # Derived from PythonVersion so the generated classifiers, tox envlist
        # and CI matrix cannot disagree with requires-python. Falls back to the
        # schema default because the generator also accepts raw dicts that
        # never went through Config.
        minimum_python = self.config.get("PythonVersion") or Config.get_field_default(
            "PythonVersion"
        )

        context = {
            **self.config,  # Spread all config values at top level
            # Same fallback: an absent threshold would render an empty
            # fail_under, which is not valid TOML.
            "CoverageThreshold": self.config.get(
                "CoverageThreshold", Config.get_field_default("CoverageThreshold")
            ),
            "config": self.config,  # Also include as nested dict for compatibility
            "cli_name": self.cli_name,
            "package_name": self.package_name,
            "profile_defaults": profile_defaults,
            "PythonVersions": python_versions_from(minimum_python),
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

        # Fail before creating anything if the formatter is unavailable
        resolve_ruff()

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
        self._generate_changelog(output_dir, groups)
        self._generate_development(output_dir)
        self._generate_license(output_dir)
        self._generate_manifest(output_dir)
        self._generate_tox(output_dir)
        self._generate_precommit(output_dir)

        # Generate .github files (conditionally)
        if self.config.get("IncludeGithubWorkflows", False):
            self._generate_github_files(github_dir, workflows_dir, issue_template_dir)

        # Generate test files
        self._generate_tests(tests_dir, groups)

        # Generate package files
        self._generate_package_init(src_dir, package_name)
        self._generate_cli_main(src_dir, package_name, groups)
        self._generate_client(src_dir)
        self._generate_logging(src_dir)
        self._generate_redaction(src_dir, groups)
        self._generate_profile(src_dir)
        self._generate_constants(src_dir, ca_file_name, splash_file_name, main_dir)

        # Generate commands
        self._generate_commands_init(commands_dir, groups)
        self._generate_config_commands(commands_dir)
        for tag, group in groups.items():
            self._generate_command_group(group, commands_dir)

        # Organise imports and format generated Python files with ruff
        self._format_generated_code(output_dir)

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

    def _generate_redaction(
        self, src_dir: Path, groups: dict[str, CommandGroup]
    ) -> None:
        """Generate the debug-output redaction module."""
        template = self.env.get_template("src/{{ PackageName }}/redaction.py.j2")
        content = template.render(
            **self._template_context(sensitive_fields=_sensitive_field_names(groups))
        )
        with open(src_dir / "redaction.py", "w") as f:
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

    def _generate_changelog(
        self, output_dir: Path, groups: dict[str, "CommandGroup"] | None = None
    ) -> None:
        """Generate CHANGELOG.md."""
        template = self.env.get_template("CHANGELOG.md.j2")
        content = template.render(**self._template_context(groups=groups or {}))
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
            # These three pin a single interpreter, which must be the project's
            # declared minimum. Hardcoding 3.12 gave a project with a higher
            # PythonVersion a CI job whose pip install fails against its own
            # requires-python.
            (".github/workflows/docs.yaml.j2", workflows_dir / "docs.yaml"),
            (
                ".github/workflows/pr-validation.yaml.j2",
                workflows_dir / "pr-validation.yaml",
            ),
            (".github/workflows/release.yaml.j2", workflows_dir / "release.yaml"),
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
            (".github/workflows/labeler.yaml", workflows_dir / "labeler.yaml"),
            (".github/workflows/sync-labels.yaml", workflows_dir / "sync-labels.yaml"),
        ]
        for template_name, output_path in static_files:
            # Use get_template to read static files through Jinja loader
            loader = self.env.loader
            if loader is not None:
                source = loader.get_source(self.env, template_name)[0]
                with open(output_path, "w") as f:
                    f.write(source)

        # test.yaml is rendered because it references the generated package name
        template = self.env.get_template(".github/workflows/test.yaml.j2")
        content = template.render(**self._template_context())
        with open(workflows_dir / "test.yaml", "w") as f:
            f.write(content)

    def _generate_tests(self, tests_dir: Path, groups: dict[str, CommandGroup]) -> None:
        """Generate test files."""
        # Generate cli_test.py directly in tests/
        template = self.env.get_template("tests/{{ PackageName }}/cli_test.py.j2")
        content = template.render(**self._template_context())
        with open(tests_dir / "cli_test.py", "w") as f:
            f.write(content)

        # One test per spec-derived command, covering the rendered output
        template = self.env.get_template("tests/{{ PackageName }}/commands_test.py.j2")
        content = template.render(**self._template_context(groups=groups))
        with open(tests_dir / "commands_test.py", "w") as f:
            f.write(content)

    @staticmethod
    def _format_generated_code(output_dir: Path) -> None:
        """Organise imports and format generated Python files with ruff.

        Line length is read from the generated pyproject.toml, so no
        --line-length flag is passed here.
        """
        ruff = resolve_ruff()
        for args in RUFF_COMMANDS:
            # --no-cache is a generator-side detail, not part of the shared
            # recipe: without it ruff writes a .ruff_cache directory into the
            # project it is formatting, polluting the output and giving it
            # non-deterministic contents.
            subcommand, *rest = args
            result = subprocess.run(
                [*ruff, subcommand, "--no-cache", *rest, str(output_dir)],
                capture_output=True,
            )
            # Ruff exits 1 for "violations remain", which is a code-quality
            # signal and must not abort generation. Exit 2 and above means
            # ruff could not do its job - unparseable code, bad config, IO
            # failure - and the output cannot be trusted.
            if result.returncode >= 2:
                details = (
                    result.stderr.decode().strip() or result.stdout.decode().strip()
                )
                raise RuntimeError(
                    f"ruff {' '.join(args)} failed on generated code: {details}"
                )
            if result.returncode == 1:
                logger.warning(
                    "ruff %s reported unresolved violations in generated code",
                    " ".join(args),
                )
