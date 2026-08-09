# Changelog

## 2.1.0

### Changes

- Supports Python 3.12, 3.13 and 3.14.
- Generated projects support Python 3.12, 3.13 and 3.14. Raising `PythonVersion` narrows that range; values outside it are rejected.
- Generated projects are formatted and linted with Ruff instead of Black and flake8, and ship a `tox -e format` environment.
- Generated code uses a line length of 88 and absolute, module-level imports.
- Ruff ships with cli-wizard, so generated code is formatted without installing anything else.
- `generate` asks for confirmation before deleting a non-empty output directory. A new `--force`/`-f` flag skips the prompt.

**Dependencies in cli-wizard**

- Upgraded click from ~8.3.1 to ~8.4.
- Upgraded pydantic from ~2.12.5 to ~2.13.
- Upgraded requests from ~2.32.5 to ~2.34.
- Added ruff ~0.16.2 as a runtime dependency.

**Dependencies in generated code**

- Upgraded click from ~8.1 to ~8.4.
- Upgraded pydantic from ~2.10 to ~2.13.
- Upgraded requests from ~2.32 to ~2.34.
- Upgraded the development dependencies: build ~1.5, mypy ~2.3, pre-commit ~4.6, pytest ~9.1, pytest-cov ~7.1, tox ~4.58 and types-requests ~2.33. Ruff ~0.16.2 replaces autoflake, black and flake8.
- Upgraded the pre-commit hooks: `pre-commit-hooks` v6.0.0 and `mirrors-mypy` v2.3.0, with `ruff-pre-commit` v0.16.2 replacing the black and flake8 hooks.
- Upgraded the GitHub Actions: `checkout` v7, `setup-python` v7, `upload-pages-artifact` v5, `deploy-pages` v5, `labeler` v7, `codeql-action` v4 and `codecov-action` v7. `b4b4r07/github-labeler` is pinned to v0.2.1 instead of tracking `@master`.
- Every dependency is pinned to the same version everywhere it is declared. The generated `tox.ini` previously left mypy, pytest, pytest-cov and the type stubs unversioned, so `tox` could resolve versions the generated `pyproject.toml` did not pin.

### Bug Fixes

- Fixed `config set` writing values the schema then rejected, which made every `config` subcommand fail until the file was deleted by hand. Values are validated before being written, and an unreadable file falls back to defaults with a warning.
- Fixed `config set` freezing derived values, so `CommandName`, `PackageName`, `RepositoryUrl` and `CopyrightYear` stopped tracking `ProjectName`.
- Fixed `config unset` writing `null` instead of removing the key, which left non-optional fields holding a value the schema rejects.
- Fixed `config get` and `config unset` exiting 0 on an unknown key.
- Fixed `IncludeTags`, `ExcludeTags`, `IncludeOperations` and `ExcludeOperations` being unsettable from the command line; they now accept a comma-separated value.
- Fixed a `TypeError` when the configuration contained an explicit `ProjectName: null`.
- Fixed a circular `#[Param]` reference hanging `generate` and `bootstrap` until memory ran out; it is now reported as an invalid configuration.
- Fixed `bootstrap` writing a `cli-wizard.yaml` it could not read back, because values containing a quote or a backslash were left unescaped.
- Fixed `PackageName` accepting values that are not valid Python identifiers, which produced a project that could not be imported.
- Fixed `Copyright (c) None` in generated file headers and the LICENSE, and `Homepage = "None"` in the generated `pyproject.toml`.
- Fixed `IncludeGithubWorkflows` always failing with a `TemplateNotFound` error.
- Fixed generated code shipping unformatted, which produced hundreds of lines of formatting-only diff on every regeneration.
- Fixed the generated test workflow pointing at the wrong package, which made it fail on a new project's first push.
- Fixed generated `tox -e lint` failing on any line longer than 79 characters.


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
