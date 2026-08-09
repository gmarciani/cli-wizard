# Changelog

## 2.1.0

### Breaking Changes

- `config unset <key>` now removes the key so the schema default applies again, instead of writing `null` into it. Writing `null` was how a non-optional field such as `ProjectName` ended up holding a value the schema rejects, which locked every `config` subcommand out of the file. The command no longer refuses any key, because removing one can never produce an invalid config.
- `config set` now writes only the keys that were explicitly set, instead of the entire merged configuration. Config files written by earlier versions contain every field and stay valid, but their derived values remain frozen at whatever they were when the file was first written; run `cli-wizard config reset` and set your values again to pick up the new behaviour.
- `config get` and `config unset` now exit non-zero on an unknown key, matching `config set`. They previously logged an error and exited 0.

### Changes

- Pinned all dependency version constraints (`~=`) to the minor version instead of the patch version.
- Increased test coverage from 71% to 98%, with new tests for the `bootstrap` command and previously untested code paths in `generate`, `CliGenerator`, and `constants`.
- Generated projects are formatted and linted with Ruff instead of Black and flake8, and ship a `tox -e format` environment that reproduces exactly how the code was generated.
- Generated code uses a line length of 88, absolute imports throughout, and no imports nested inside functions.
- Ruff is bundled with cli-wizard, so generated code is formatted without installing anything else.
- `generate` now asks for confirmation before deleting a non-empty output directory, naming the directory and stating that its entire contents will be removed. Declining leaves the directory untouched and exits non-zero. A new `--force`/`-f` flag skips the prompt, matching the flag `bootstrap` already provides. Empty and non-existent output directories proceed without prompting.
- Python 3.12, 3.13 and 3.14 support is now verified rather than only declared.
  cli-wizard's `tox` gained `py312`, `py313` and `py314` environments — it
  previously ran the suite on a single interpreter — and its CI runs one job per
  version. 3.13 was never executed anywhere before: CI tested 3.14 in one
  workflow and 3.12 in another, while the classifiers claimed all three.
- Generated projects derive their supported versions from `PythonVersion`
  instead of hardcoding 3.12 to 3.14. That one value now drives the classifiers,
  the `tox` envlist, ruff's `target-version` and the CI matrix, alongside
  `requires-python`. A project generated with `PythonVersion: "3.13"` no longer
  claims 3.12 support anywhere. `PythonVersion` is validated against the
  supported set, so an unsupported value is rejected instead of producing a
  project that claims support cli-wizard never tested.

**Dependencies in cli-wizard**

- Upgraded click from ~8.3.1 to ~8.4.
- Upgraded pydantic from ~2.12.5 to ~2.13.
- Upgraded requests from ~2.32.5 to ~2.34.
- Added ruff ~0.16.2 as a runtime dependency.

**Dependencies in generated code**

- Upgraded click from ~8.1 to ~8.4.
- Upgraded pydantic from ~2.10 to ~2.13.
- Upgraded requests from ~2.32 to ~2.34.
- Upgraded the development dependencies: build from ~1.3 to ~1.5, mypy from
  ~1.18 to ~2.3, pre-commit from ~4.0 to ~4.6, pytest from ~9.0 to ~9.1,
  pytest-cov from ~7.0 to ~7.1, tox from ~4.32 to ~4.58, and types-requests from
  ~2.32 to ~2.33. Ruff ~0.16.2 replaces autoflake, black and flake8.
- Pinned the dependencies of the generated `tox.ini`, which left mypy, pytest,
  pytest-cov, types-PyYAML and types-requests unversioned. `tox -e test` and
  `tox -e lint` therefore resolved whatever was newest at the time they ran,
  which could differ from the versions the generated `pyproject.toml` pinned.
  Every dependency shared between cli-wizard and the generated code now carries
  the same version everywhere it is declared.
- Upgraded the pre-commit hooks: `pre-commit-hooks` from v5.0.0 to v6.0.0 and
  `mirrors-mypy` from v1.15.0 to v2.3.0, which had lagged four majors behind the
  mypy pinned in the generated `pyproject.toml`. `ruff-pre-commit` v0.16.2
  replaces the black and flake8 hooks.
- Upgraded the GitHub Actions used by the generated workflows:
  `actions/checkout` from v4 to v7, `actions/setup-python` from v4 (v5 in
  `release.yaml`) to v7, `actions/upload-pages-artifact` from v3 to v5,
  `actions/deploy-pages` from v4 to v5, `actions/labeler` from v5 to v7,
  `github/codeql-action` from v3 to v4, and `codecov/codecov-action` from v5 to
  v7.
- Pinned `b4b4r07/github-labeler` in the generated `sync-labels.yaml` to v0.2.1.
  It tracked `@master`, so every run executed whatever that branch happened to
  point at.

### Bug Fixes

- Fixed the generated `docs`, `release` and `pr-validation` workflows pinning
  Python 3.12 regardless of the project's `PythonVersion`. They were copied
  byte-for-byte rather than rendered, so a project with a higher minimum got CI
  that installed 3.12 and then failed `pip install -e .` against its own
  `requires-python`. All three are now templates that follow the declared
  minimum.
- Fixed `pre-commit run --all-files` failing on an E402 in `docs/conf.py`. The
  import has to follow the `sys.path.insert` that makes the package importable,
  so it is now marked `# noqa: E402`. `tox -e lint` never caught this because it
  only scans `src/cli_wizard` and `tests/`, while pre-commit scans every file.
- Fixed `IncludeGithubWorkflows` generation, which always failed with a `TemplateNotFound` error due to a filename mismatch between the `changelog-enforcer.yaml` workflow template and its reference in the generator.
- Fixed generated code shipping unformatted, which produced hundreds of lines of formatting-only diff every time a CLI was regenerated.
- Fixed the generated GitHub test workflow pointing at the wrong package, which made it fail on the first push of a new project.
- Fixed generated `tox -e lint` failing on any line longer than 79 characters despite the code being formatted to a wider width.
- Fixed `PackageName` accepting values that are not valid Python identifiers, which produced a project that could not be imported.
- Fixed `Copyright (c) None` appearing in generated file headers and the LICENSE, and `Homepage = "None"` in the generated `pyproject.toml`.
- Fixed `bootstrap` writing a `cli-wizard.yaml` it could not read back: string values were wrapped in double quotes with nothing inside them escaped, so a value containing a quote or a backslash — a description with a quotation mark, any Windows-style path — produced a file that failed to parse, and `bootstrap` broke reloading its own output. Values are now escaped when written, and every value accepted at a prompt survives the round trip unchanged.
- Fixed a circular `#[Param]` reference in the configuration hanging `generate` and `bootstrap` forever, growing the value until memory ran out. Expansion now terminates on any input and reports the offending parameter and value as an invalid configuration. References to parameters that do not exist are still left as written.
- Fixed `config set` accepting any key and value without validation, which wrote a configuration file that the schema then rejected on every subsequent read. `show`, `get`, `set`, `unset` and `reset` all exited with a traceback, so the documented recovery path was itself unusable and only deleting `~/.cli_wizard/cli-wizard.yaml` by hand restored the tool. Values are now validated and coerced before being written, unknown keys are rejected, and an unreadable or invalid file falls back to schema defaults with a warning rather than raising.
- Fixed `config set` freezing derived values into the configuration file. Setting any key wrote back all ~45 fields, so `CommandName`, `PackageName`, `RepositoryUrl` and `CopyrightYear` stopped tracking `ProjectName` from that point on, and a later `ProjectName` change silently generated projects carrying the old names.
- Fixed a `TypeError` when the configuration contained an explicit `ProjectName: null`. Name derivation defaulted only a missing key, not a null one, and passed `None` to `re.sub`.
- Fixed list-valued configuration fields being unsettable from the command line. `IncludeTags`, `ExcludeTags`, `IncludeOperations` and `ExcludeOperations` now accept a comma-separated value, and the mapping fields `TagMapping` and `CommandMapping` are rejected with a message pointing at the configuration file instead of corrupting it.


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
