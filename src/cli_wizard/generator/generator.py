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
from cli_wizard.errors import ConfigError, FormattingError, RuffNotFoundError
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


def _option_doc(
    usage: str,
    *,
    required: bool,
    repeatable: bool = False,
    description: str = "",
    default: Any = None,
) -> dict[str, Any]:
    """Describe one option for the README, the way Click's help would."""
    return {
        "usage": usage,
        "required": required,
        "repeatable": repeatable,
        "description": description,
        # Click shows a boolean default in lower case, so the README does too.
        "default": (
            None
            if default is None
            else str(default).lower()
            if isinstance(default, bool)
            else str(default)
        ),
    }


def _operation_options(op: Operation) -> list[dict[str, Any]]:
    """List the options of one spec-derived command, in the order they are declared."""
    options = []
    for param in op.path_parameters:
        options.append(
            _option_doc(
                f"--{param.cli_name} {param.metavar}",
                required=True,
                description=param.description,
            )
        )
    for param in op.query_parameters:
        options.append(
            _option_doc(
                f"--{param.cli_name} {param.metavar}",
                required=param.required,
                repeatable=param.is_array,
                description=param.description,
                default=param.default,
            )
        )
    for prop in op.body_properties:
        # A boolean property is a flag pair, unless it repeats as an array
        if prop.click_type == "bool" and not prop.is_array:
            usage = f"--{prop.cli_name}/--no-{prop.cli_name}"
        else:
            usage = f"--{prop.cli_name} {prop.metavar}"
        options.append(
            _option_doc(
                usage,
                required=prop.required,
                repeatable=prop.is_array,
                description=prop.description,
                default=prop.default,
            )
        )
    return options


# The built-in profile commands, documented next to the spec-derived ones.
_PARAM_OPTION = _option_doc(
    "--param TEXT", required=True, description="Parameter name."
)
_VALUE_OPTION = _option_doc(
    "--value TEXT", required=True, description="Parameter value."
)
_CONFIG_COMMANDS: list[tuple[str, str, list[dict[str, Any]]]] = [
    ("get", "Get a configuration value from a profile.", [_PARAM_OPTION]),
    ("init", "Initialize the profile file with default profile.", []),
    ("list-profiles", "List all available profiles.", []),
    ("set", "Set a configuration value in a profile.", [_PARAM_OPTION, _VALUE_OPTION]),
    ("show", "Show all parameters and values for a profile.", []),
    ("unset", "Remove a configuration value from a profile.", [_PARAM_OPTION]),
]


def _readme_command(name: str, summary: str, options: list[dict[str, Any]]) -> dict:
    """Describe one command for the README, with the anchor of its heading.

    The name is the group and the command alone, without the executable, which
    the reference would otherwise repeat on every line. GitHub derives the
    anchor from the heading by lower-casing it and turning spaces into hyphens;
    command names are already kebab-case, so that is all.
    """
    return {
        "name": name,
        "anchor": name.replace(" ", "-"),
        "summary": summary,
        "options": options,
    }


def _readme_groups(groups: dict[str, CommandGroup]) -> list[dict]:
    """Build the command reference of the README, groups and commands sorted by name.

    The built-in config group is slotted in alphabetically with the spec-derived
    ones, so the index at the top of the section and the subsections below it
    read in the same order.
    """
    reference = [
        {
            "name": "config",
            "description": "Configure the CLI.",
            "commands": [
                _readme_command(f"config {command}", summary, options)
                for command, summary, options in _CONFIG_COMMANDS
            ],
        }
    ]
    for group in groups.values():
        reference.append(
            {
                "name": group.cli_name,
                "description": group.description,
                "commands": [
                    _readme_command(
                        f"{group.cli_name} {op.command_name}",
                        op.summary or op.operation_id,
                        _operation_options(op),
                    )
                    for op in sorted(group.operations, key=lambda o: o.command_name)
                ],
            }
        )
    return sorted(reference, key=lambda g: g["name"])


# What each profile setting does, for the generated README. Only the keys the
# generated code resolves belong here: PROFILE_DEFAULTS also carries keys that
# nothing reads yet, and advertising those would document behaviour the CLI
# does not have. A test checks this against the resolve_setting() calls.
PROFILE_SETTING_DOCS: dict[str, str] = {
    "baseUrl": "Base URL of the API every command sends its requests to.",
    "accessToken": (
        "Bearer token sent in the `Authorization` header of every request."
    ),
    "timeout": "Seconds to wait for a response before a request fails.",
    "outputFormat": (
        "How a command prints the response: `json`, `yaml` or `table`. "
        "`--output` overrides it for one invocation."
    ),
    "jsonIndent": "Indentation of the JSON a command prints.",
    "tableStyle": (
        "Borders of a `table` output: `rounded`, `ascii`, `minimal` or `markdown`."
    ),
    "logLevel": "Lowest level of log message shown: DEBUG, INFO, WARNING or ERROR.",
    "outputColors": "Whether log messages and errors are coloured.",
    "retryMaxAttempts": (
        "Retries of a request that could not connect or got a 429 or 5xx "
        "response, after the first attempt. `0` sends every request once."
    ),
    "retryBackoffFactor": (
        "Seconds waited before retry *n*: the factor times 2^(n-1), or what a "
        "`Retry-After` header asks."
    ),
}


# Templates rendered with the shared context alone, and where each one lands,
# relative to the output directory. The literal "{{ PackageName }}" in a
# destination is resolved by substitution, as it is in the templates tree.
PLAIN_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("pyproject.toml.j2", "pyproject.toml"),
    ("VERSION.j2", "VERSION"),
    (".gitignore.j2", ".gitignore"),
    ("Makefile.j2", "Makefile"),
    ("DEVELOPMENT.md.j2", "DEVELOPMENT.md"),
    ("LICENSE.j2", "LICENSE"),
    ("MANIFEST.in.j2", "MANIFEST.in"),
    ("tox.ini.j2", "tox.ini"),
    ("pre-commit-config.yaml.j2", ".pre-commit-config.yaml"),
    ("tests/{{ PackageName }}/cli_test.py.j2", "tests/cli_test.py"),
    ("src/{{ PackageName }}/__init__.py.j2", "src/{{ PackageName }}/__init__.py"),
    ("src/{{ PackageName }}/client.py.j2", "src/{{ PackageName }}/client.py"),
    ("src/{{ PackageName }}/errors.py.j2", "src/{{ PackageName }}/errors.py"),
    ("src/{{ PackageName }}/log.py.j2", "src/{{ PackageName }}/log.py"),
    ("src/{{ PackageName }}/options.py.j2", "src/{{ PackageName }}/options.py"),
    ("src/{{ PackageName }}/output.py.j2", "src/{{ PackageName }}/output.py"),
    ("src/{{ PackageName }}/profile.py.j2", "src/{{ PackageName }}/profile.py"),
    ("src/{{ PackageName }}/runner.py.j2", "src/{{ PackageName }}/runner.py"),
    ("src/{{ PackageName }}/state.py.j2", "src/{{ PackageName }}/state.py"),
    (
        "src/{{ PackageName }}/commands/__init__.py.j2",
        "src/{{ PackageName }}/commands/__init__.py",
    ),
    (
        "src/{{ PackageName }}/commands/config.py.j2",
        "src/{{ PackageName }}/commands/config.py",
    ),
)

# The .github tree, generated only when IncludeGithubWorkflows is set. The
# templated files reference the project; the three workflows pinning a single
# interpreter must pin the project's declared minimum, since a hardcoded
# version gave a project with a higher PythonVersion a CI job whose pip
# install failed against its own requires-python.
GITHUB_TEMPLATES: tuple[tuple[str, str], ...] = (
    (".github/CODEOWNERS.j2", ".github/CODEOWNERS"),
    (".github/labels.yaml.j2", ".github/labels.yaml"),
    (
        ".github/ISSUE_TEMPLATE/bug-report.yml.j2",
        ".github/ISSUE_TEMPLATE/bug-report.yml",
    ),
    (".github/ISSUE_TEMPLATE/config.yml.j2", ".github/ISSUE_TEMPLATE/config.yml"),
    (
        ".github/ISSUE_TEMPLATE/feature-request.yml.j2",
        ".github/ISSUE_TEMPLATE/feature-request.yml",
    ),
    (".github/workflows/docs.yaml.j2", ".github/workflows/docs.yaml"),
    (".github/workflows/pr-validation.yaml.j2", ".github/workflows/pr-validation.yaml"),
    (".github/workflows/release.yaml.j2", ".github/workflows/release.yaml"),
    (".github/workflows/test.yaml.j2", ".github/workflows/test.yaml"),
)

# Copied byte for byte, so they cannot reference the generated project
STATIC_FILES: tuple[str, ...] = (
    ".github/dependabot.yaml",
    ".github/labeler.yaml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/changelog-enforcer.yaml",
    ".github/workflows/codeql.yaml",
    ".github/workflows/labeler.yaml",
    ".github/workflows/sync-labels.yaml",
)

# Config keys naming files copied into the generated package's resources/,
# resolved relative to the configuration file; each must exist when set
RESOURCE_KEYS: tuple[str, ...] = ("CaFile", "SplashFile")

# Ruff invocations applied to generated code, as (args...) without the binary
# or the target path. The generated tox.ini [testenv:format] must run the same
# commands; test_format_recipe_matches_tox_template enforces that.
RUFF_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("check", "--fix"),
    ("format",),
)


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
        self.env = Environment(  # noqa: S701 - renders source files, not HTML
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
        # Build profile defaults from config. Every parameter gets an entry even
        # when the config omits it: the generated CLI resolves settings against
        # this mapping, and a missing key would leave the setting unresolvable.
        profile_defaults = {
            profile_key: self.config.get(
                config_key, Config.get_field_default(config_key)
            )
            for config_key, profile_key in self.PROFILE_PARAM_FIELDS.items()
        }
        # Runtime-only profile parameters (not derived from wizard config)
        profile_defaults["accessToken"] = None

        # The values a Literal-typed setting accepts, so the generated CLI can
        # reject a profile or environment value outside them.
        profile_choices = {
            profile_key: Config.get_field_choices(config_key)
            for config_key, profile_key in self.PROFILE_PARAM_FIELDS.items()
            if Config.get_field_choices(config_key) is not None
        }

        # Derived from PythonVersion so the generated classifiers, tox envlist
        # and CI matrix cannot disagree with requires-python. Falls back to the
        # schema default because the generator also accepts raw dicts that
        # never went through Config.
        minimum_python = self.config.get("PythonVersion") or Config.get_field_default(
            "PythonVersion"
        )

        # Documented in the order the README should read them, with the default
        # the generated constants module ends up holding.
        profile_settings = [
            (key, profile_defaults[key], text)
            for key, text in PROFILE_SETTING_DOCS.items()
        ]

        context = {
            **self.config,  # Spread all config values at top level
            # Same fallback: an absent threshold would render an empty
            # fail_under, which is not valid TOML.
            "CoverageThreshold": self.config.get(
                "CoverageThreshold", Config.get_field_default("CoverageThreshold")
            ),
            "Version": self.config.get("Version", Config.get_field_default("Version")),
            "config": self.config,  # Also include as nested dict for compatibility
            "cli_name": self.cli_name,
            "package_name": self.package_name,
            "profile_defaults": profile_defaults,
            "profile_choices": profile_choices,
            "profile_settings": profile_settings,
            # The same expression the constants module expands at runtime, so
            # the README names the file the CLI really reads.
            "profile_file": self.config.get("ProfileFile")
            or f"{self._compute_main_dir(self.package_name)}/profiles.yaml",
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

        # Fail before creating anything if the formatter or a resource is missing
        resolve_ruff()
        self.check_resources()

        output_dir.mkdir(parents=True, exist_ok=True)

        src_dir = output_dir / "src" / package_name
        commands_dir = src_dir / "commands"
        resources_dir = src_dir / "resources"
        tests_dir = output_dir / "tests"
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Resources (the CA and splash files), then what their names feed
        ca_file_name = self._copy_resource("CaFile", resources_dir)
        splash_file_name = self._copy_resource("SplashFile", resources_dir)
        main_dir = self._compute_main_dir(package_name)

        for template_name, relative in PLAIN_TEMPLATES:
            self._render(template_name, self._destination(output_dir, relative))
        self._render(
            "README.md.j2",
            output_dir / "README.md",
            readme_groups=_readme_groups(groups),
        )
        self._render("CHANGELOG.md.j2", output_dir / "CHANGELOG.md", groups=groups)
        self._render(
            "tests/{{ PackageName }}/commands_test.py.j2",
            tests_dir / "commands_test.py",
            groups=groups,
        )
        self._render(
            "src/{{ PackageName }}/cli.py.j2", src_dir / "cli.py", groups=groups
        )
        self._render(
            "src/{{ PackageName }}/redaction.py.j2",
            src_dir / "redaction.py",
            sensitive_fields=_sensitive_field_names(groups),
        )
        self._render(
            "src/{{ PackageName }}/constants.py.j2",
            src_dir / "constants.py",
            ca_file_name=ca_file_name,
            splash_file_name=splash_file_name,
            main_dir=main_dir,
        )
        for group in groups.values():
            self._render(
                "src/{{ PackageName }}/commands/group.py.j2",
                commands_dir / f"{group.module_name}.py",
                group=group,
            )

        if self.config.get("IncludeGithubWorkflows", False):
            for template_name, relative in GITHUB_TEMPLATES:
                self._render(template_name, output_dir / relative)
            for name in STATIC_FILES:
                self._copy_static(name, output_dir / name)

        # Organise imports and format generated Python files with ruff
        self._format_generated_code(output_dir)

    def _destination(self, output_dir: Path, relative: str) -> Path:
        """Resolve where a template lands, substituting the package name."""
        return output_dir / relative.replace("{{ PackageName }}", self.package_name)

    def _render(self, template_name: str, destination: Path, **extra: Any) -> None:
        """Render a template with the shared context, plus extra, into a file."""
        template = self.env.get_template(template_name)
        content = template.render(**self._template_context(**extra))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)

    def _copy_static(self, name: str, destination: Path) -> None:
        """Copy a file of the templates tree byte for byte, through the loader."""
        loader = self.env.loader
        if loader is None:
            return
        source = loader.get_source(self.env, name)[0]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source)

    def check_resources(self) -> None:
        """Fail if a configured resource file does not exist.

        A missing CA file would leave the generated CLI trusting the system
        store instead of the pinned CA, so a missing file is an error, never
        skipped. Callers run this before deleting the previous output.
        """
        for key in RESOURCE_KEYS:
            path = self._resource_path(key)
            if path is not None and not path.is_file():
                raise ConfigError(f"{key} '{path}' not found")

    def _resource_path(self, key: str) -> Path | None:
        """Resolve the file a config key names, relative to the config file."""
        configured = self.config.get(key)
        if not configured:
            return None
        path = Path(configured)
        if not path.is_absolute():
            path = self.config_dir / path
        return path

    def _copy_resource(self, key: str, resources_dir: Path) -> str | None:
        """Copy the file a config key names into resources, returning its name.

        Nothing is copied, and None returned, when the key is unset; a missing
        file is rejected earlier by check_resources().
        """
        path = self._resource_path(key)
        if path is None:
            return None
        shutil.copy2(path, resources_dir / path.name)
        return path.name

    def _compute_main_dir(self, package_name: str) -> str:
        """Get main directory path from config.

        The #[Param] references should already be resolved by config loader.
        ${VAR} environment variables are kept as-is for runtime expansion.
        """
        main_dir = self.config.get("MainDir")
        if main_dir is not None:
            return str(main_dir)
        return f"${{HOME}}/.{package_name}"

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
            result = subprocess.run(  # noqa: S603 - fixed argv, no shell
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
                raise FormattingError(
                    f"ruff {' '.join(args)} failed on generated code: {details}"
                )
            if result.returncode == 1:
                logger.warning(
                    "ruff %s reported unresolved violations in generated code",
                    " ".join(args),
                )
