# Changelog

## 3.0.0

### New Features

#### cli-wizard

- Added the `HomePageUrl` config parameter, which sets `Homepage` in a generated `pyproject.toml` and defaults to `RepositoryUrl`.

### Changes

#### cli-wizard

- Publishes no extras: the dev, test and docs toolchains are [PEP 735](https://peps.python.org/pep-0735/) groups, `dev` including the other two.
- Installing them is `pip install -e . --group dev`, which needs pip 25.1 or newer.

#### Generated code

- Publishes no extras: the dev, test and docs toolchains are PEP 735 dependency groups, and `dev` includes the other two.
- Installing them is `pip install -e . --group dev`, which needs pip 25.1 or newer.

### Bug Fixes

#### Generated code

- Fixed `${HOME}` in `MainDir`, `ProfileFile` and `LogFile` staying literal wherever `HOME` is unset. Home now resolves through `Path.home()`.
- Fixed `--version` reporting `0.0.0` when installed from a wheel; the version now comes from the installed package metadata instead of a `VERSION` file next to the source.
- Fixed `tox` running the tests only, because ruff and mypy were left out of the default `envlist`.
- Fixed the PR validation workflow measuring coverage of `cli_wizard` instead of the generated package.
- Fixed that workflow and `DEVELOPMENT.md` calling `tox -e test`, `type` and `coverage`, which `tox.ini` never defined.
- Fixed `DEVELOPMENT.md` documenting `make setup`, a target the generated `Makefile` never defined.
- Fixed the docs workflow installing a `[docs]` extra the generated `pyproject.toml` does not declare.
- Fixed the splash screen printing at import time, which put it in `--help` and `--version` output and corrupted the shell completion stream. It now prints from the CLI callback.


## 2.1.0

### Changes

#### cli-wizard

- Supports Python 3.12, 3.13 and 3.14.
- `generate` asks for confirmation before deleting a non-empty output directory. A new `--force`/`-f` flag skips the prompt.
- Ruff is bundled, so generated code is formatted without installing anything else.
- Upgraded click from ~8.3.1 to ~8.4.
- Upgraded pydantic from ~2.12.5 to ~2.13.
- Upgraded requests from ~2.32.5 to ~2.34.
- Added ruff ~0.16.2 as a runtime dependency.

#### Generated code

- Supports Python 3.12, 3.13 and 3.14. Raising `PythonVersion` narrows that range; values outside it are rejected.
- Formatted and linted with Ruff instead of Black and flake8, with a `tox -e format` environment.
- Uses a line length of 88 and absolute, module-level imports.
- Upgraded click from ~8.1 to ~8.4.
- Upgraded pydantic from ~2.10 to ~2.13.
- Upgraded requests from ~2.32 to ~2.34.
- Upgraded build from ~1.3 to ~1.5.
- Upgraded mypy from ~1.18 to ~2.3.
- Upgraded pre-commit from ~4.0 to ~4.6.
- Upgraded pytest from ~9.0 to ~9.1.
- Upgraded pytest-cov from ~7.0 to ~7.1.
- Upgraded tox from ~4.32 to ~4.58.
- Upgraded types-requests from ~2.32 to ~2.33.
- Added ruff ~0.16.2, replacing autoflake, black and flake8.
- Upgraded the `pre-commit-hooks` hook from v5.0.0 to v6.0.0.
- Upgraded the `mirrors-mypy` hook from v1.15.0 to v2.3.0.
- Added the `ruff-pre-commit` v0.16.2 hook, replacing the black and flake8 hooks.
- Upgraded `actions/checkout` from v4 to v7.
- Upgraded `actions/setup-python` from v4 (v5 in `release.yaml`) to v7.
- Upgraded `actions/upload-pages-artifact` from v3 to v5.
- Upgraded `actions/deploy-pages` from v4 to v5.
- Upgraded `actions/labeler` from v5 to v7.
- Upgraded `github/codeql-action` from v3 to v4.
- Upgraded `codecov/codecov-action` from v5 to v7.
- Pinned `b4b4r07/github-labeler` to v0.2.1 instead of tracking `@master`.
- Pinned mypy, pytest, pytest-cov and the type stubs in the generated `tox.ini`, which left them unversioned. Every dependency now carries the same version everywhere it is declared.

### Bug Fixes

#### cli-wizard

- Fixed `config set` writing values the schema then rejected, which made every `config` subcommand fail until the file was deleted by hand. Values are validated before being written, and an unreadable file falls back to defaults with a warning.
- Fixed `config set` freezing derived values, so `CommandName`, `PackageName`, `RepositoryUrl` and `CopyrightYear` stopped tracking `ProjectName`.
- Fixed `config unset` writing `null` instead of removing the key, which left non-optional fields holding a value the schema rejects.
- Fixed `config get` and `config unset` exiting 0 on an unknown key.
- Fixed `IncludeTags`, `ExcludeTags`, `IncludeOperations` and `ExcludeOperations` being unsettable from the command line; they now accept a comma-separated value.
- Fixed a `TypeError` when the configuration contained an explicit `ProjectName: null`.
- Fixed `PackageName` accepting values that are not valid Python identifiers, which produced a project that could not be imported.
- Fixed a circular `#[Param]` reference hanging `generate` and `bootstrap` until memory ran out; it is now reported as an invalid configuration.
- Fixed `bootstrap` writing a `cli-wizard.yaml` it could not read back, because values containing a quote or a backslash were left unescaped.
- Fixed `IncludeGithubWorkflows` always failing with a `TemplateNotFound` error.

#### Generated code

- Fixed code shipping unformatted, which produced hundreds of lines of formatting-only diff on every regeneration.
- Fixed `tox -e lint` failing on any line longer than 79 characters.
- Fixed the test workflow pointing at the wrong package, which made it fail on a new project's first push.
- Fixed `Copyright (c) None` in file headers and the LICENSE, and `Homepage = "None"` in `pyproject.toml`.


## 2.0.0

### New Features

- Added `bootstrap` command to scaffold a CLI project with a step-by-step guided procedure — no OpenAPI file required
- Added config parameters: `ProjectName`, `CommandName`, `PackageName`, `Description`, `Version`,
  `AuthorName`, `AuthorEmail`, `GithubUser`, `PythonVersion`, `IncludeOperations`,
  `ExcludeOperations`, `IncludeGithubWorkflows`, `CopyrightYear`, `RepositoryUrl`
- Added automatic derivation of `CommandName` (kebab-case), `PackageName` (snake_case), and `RepositoryUrl` from `ProjectName` and `GithubUser`, making all three fields optional
- Added dynamic command documentation in generated CHANGELOG, listing all command groups and their operations


### Changes

- `generate` command now works with or without an OpenAPI spec (`--api` flag controls API command generation)
- All config subcommands now support the `--debug` output flag
- Profile defaults are built from config values and merged at runtime for consistent behavior
- Improved generated project tooling: `pyproject.toml` includes mypy overrides for click and requests, and all generated Python files are auto-formatted with Black
- Removed deprecated `OutputDir` parameter from config schema
- Updated Python target version from 3.11 to 3.12
- Improved formatting and consistency across all templates
- Removed deprecated sample config from examples
- Upgraded click from ~8.1 to ~8.3.1
- Upgraded Jinja2 from ~3.1 to ~3.1.6
- Upgraded pydantic from ~2.10 to ~2.12.5
- Upgraded PyYAML from ~6.0 to ~6.0.3
- Upgraded requests from ~2.32 to ~2.32.5
- Upgraded build from ~1.3 to ~1.4
- Upgraded mypy from ~1.18 to ~1.19
- Upgraded pre-commit from ~4.0 to ~4.5
- Upgraded tox from ~4.32 to ~4.34
- Upgraded sphinx-click from ~6.0 to ~6.2
- Upgraded sphinx-rtd-theme from ~3.0 to ~3.1
- Upgraded Black to 26.1.0 in pre-commit configuration

### Bug Fixes

- All Jinja templates are now bundled into the package data, ensuring nothing is missing at runtime
- Fixed injection of config variables into Jinja templates


## 1.0.0

🎉 **Initial Release**

CLI Wizard transforms your OpenAPI specifications into customizable Python CLIs powered by the Click framework.

### Features

**Code Generation**
- Generate complete Python CLI projects from OpenAPI v3 specifications
- Automatic command grouping based on OpenAPI tags
- Automatic help generation for all commands
- Clean, colored terminal output
- `--debug` flag for verbose logging
- Built-in API client with configurable base URL and timeout
- SSL/TLS support with custom CA certificate bundles
- `--ca-file` option to specify custom CA certificates at runtime
- `--no-verify-ssl` flag to disable certificate verification

**Customization**
- YAML-based configuration for full customization
- Configurable output directory and package name
- Tag inclusion/exclusion filters
- Custom command naming via `TagMapping` and `CommandMapping`
- Customizable splash screen with color support
- Configurable logging with colors, file output, and rotation
- Profile management for storing credentials and settings

**Developer Experience**
- Generated projects are pip-installable out of the box
- Auto-generated `pyproject.toml`, `README.md`, and `VERSION`
- Resources (CA certs, splash files) bundled in the package

### Commands

- `cli-wizard generate` - Generate a CLI from an OpenAPI spec and config file
