# Changelog

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
