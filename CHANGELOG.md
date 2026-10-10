# Changelog

## 3.0.0

### New Features

#### cli-wizard

- Added the `HomePageUrl` configuration parameter, the `Homepage` of the generated `pyproject.toml`; it defaults to `RepositoryUrl`.
- Added `--project-name` to `generate`, which makes the configuration file optional: `cli-wizard generate --api openapi.yaml --project-name "My CLI"` is enough.
- Added the `CoverageThreshold` configuration parameter: a generated project's checks fail when its test coverage drops below it, 80% by default.

#### Generated code

- The generated `README.md` documents the CLI itself: a quick start, every command with its options, the settings with their defaults and precedence, and how the access token is stored and sent.
- Added `--timeout`, which sets the request timeout for one invocation.
- Added the repeatable `--header`/`-H` option, which sends an extra `Name: value` header with the request.
- Requests identify the CLI by name and version in their `User-Agent` header, so its traffic can be told apart in the server's logs.

### Changes

#### cli-wizard

- [Breaking] `generate` and `bootstrap` take the output directory with `--output`, defaulting to `CommandName` next to the configuration file; one holding that file, the OpenAPI spec, the CA file or the splash file is refused.
- [Breaking] Renamed the `OpenapiSpec` configuration parameter to `Api`, matching `--api`; a configuration still using `OpenapiSpec` is rejected.
- [Breaking] Every command prints one JSON document on stdout: `generate` and `bootstrap` print a summary of what they produced, while progress, prompts and hints go to stderr.
- [Breaking] Every failure is a JSON document on stdout, `{"error": {"type", "message", "exitCode"}}`, in place of a message on stderr.
- [Breaking] `bootstrap` asks before overwriting an existing configuration file and keeps none of its values; declining exits without writing anything, and `--force` overwrites without asking.
- A malformed OpenAPI spec and a failing ruff run are reported as errors instead of tracebacks; `--debug` logs the traceback of an unexpected error.
- The development toolchain installs with `pip install -e . --group dev`, a [PEP 735](https://peps.python.org/pep-0735/) dependency group needing pip 25.1 or newer, instead of extras.
- Logs through the standard library's `logging` module.

#### Generated code

- [Breaking] A failed command exits with the code of its failure instead of always 1: 3 no response, 4 request rejected, 5 server error, 6 undecodable response, 7 profile file, 8 bug; 2 stays usage.
- [Breaking] Every failure is a JSON document on stdout, `{"error": {"type", "message", "exitCode"}}`, never coloured and indented as `jsonIndent` says; logs stay on stderr.
- [Breaking] A response with no body prints `{"status": "success"}` in the selected output format instead of the word `Success`.
- A script that tested for exit code 1 must test for a non-zero code; the generated `README.md` documents every code.
- A 200 whose body is not valid JSON is reported as an undecodable response rather than as a failed request.
- `PythonVersion` defaults to 3.14 instead of 3.12; set it explicitly to keep targeting older interpreters.
- The development toolchain installs with `pip install -e . --group dev`, a PEP 735 dependency group needing pip 25.1 or newer, instead of extras.
- Linted with the `B` (bugbear), `S` (bandit) and `UP` (pyupgrade) ruff rule sets on top of `E`, `F`, `W` and `I`.
- Logs through the standard library's `logging` module.
- The `config` commands accept the common options, so `--profile` applies to them whether given before `config` or after the subcommand.
- The settings, the loaded profile and the log file belong to one invocation: a CLI run in-process starts clean, and the log file is closed when the run ends.

### Bug Fixes

#### cli-wizard

- Fixed a `CaFile` that does not exist being ignored, leaving the generated CLI to trust the system store instead of the pinned CA; `generate` now fails with a configuration error naming the path, before deleting the previous output.
- Fixed a `SplashFile` that does not exist being ignored silently; `generate` fails with a configuration error naming the path, as for `CaFile`.

#### Generated code

- Fixed `OutputFormat` and `TableStyle` having no effect: responses print as `json`, `yaml` or `table` as configured, and `--output`/`-o` picks a format for one invocation.
- Fixed a profile or environment value outside a setting's allowed values, such as `outputFormat: xml`, being accepted silently; it is ignored with a warning listing the allowed values.
- Fixed `RetryMaxAttempts` and `RetryBackoffFactor` having no effect: connection failures and 429 or 5xx responses are retried as configured.
- Fixed `--debug` printing passwords, tokens and the `Authorization` header in cleartext; they are redacted to `***` in the terminal and in the log file.
- Fixed `config set` logging the value it stores in cleartext; an access token or other credential is logged as `***`.
- Fixed an unknown `--profile` being logged and then ignored, sending the request with the defaults; an API command fails with exit code 7 before sending anything, listing the profiles that exist.
- Fixed a configured CA file that does not exist being ignored in favour of the system trust store; the command now fails with a configuration error.
- Fixed `CaFile` having no effect: requests are verified against the bundled CA instead of the system trust store.
- Fixed `SplashFile` having no effect: the bundled splash screen now shows.
- Fixed the profile file, which may hold secrets, being created world-readable; it is now `0600` in a `0700` directory, and `config set` tightens a file left loose by an older version.
- Fixed `--no-verify-ssl` disabling TLS verification silently; every run using it prints a warning on stderr.
- Fixed path and query parameter values never reaching the request: `get-user --user-id 42` now requests `/users/42`, and every method sends its query string.
- Fixed `--profile`, `--debug`, `--base-url`, `--no-verify-ssl` and `--ca-file` given at the root being ignored by subcommands; they are inherited, and a repeat at the subcommand level wins.
- Fixed nullable parameters and body properties, an `anyOf`/`oneOf` with a single non-null member, being typed as strings; an optional integer is now an integer.
- Fixed array parameters keeping only the last value; they are repeatable, `--tag a --tag b`, and sent as a JSON list of the declared element type.
- Fixed profile settings other than `accessToken` never applying; every setting is resolved from the flag, then `<PACKAGE>_<SETTING>` in the environment, then the profile, then the default.
- Fixed `${HOME}` in `MainDir`, `ProfileFile` and `LogFile` staying literal when `HOME` is unset.
- Fixed `--version` reporting `0.0.0` when installed from a wheel.
- Fixed the log file growing without bound; the `LogRotation*` settings now take effect.
- Fixed a bare `tox` running the tests only; it now lints and type-checks too.
- Fixed the PR validation workflow measuring coverage of `cli_wizard` instead of the generated package.
- Fixed `Jinja2` and `pydantic` being installed as runtime dependencies the generated code never imports.
- Fixed `DEVELOPMENT.md` and the workflows calling a `make setup` target and tox environments that did not exist.
- Fixed the docs workflow installing a `[docs]` extra the generated `pyproject.toml` does not declare.
- Fixed the splash screen printing on import, which corrupted `--help`, `--version` and shell completion output.
- Fixed command errors dropping the response body; the fields the API rejected are now reported, redacted and truncated past 2000 characters.
- Fixed the generated `CHANGELOG.md` shipping an empty `### Features` placeholder that could reach published release notes.
- Fixed boolean body fields always being sent: `--enabled/--no-enabled` is sent only when given, so a `PATCH` can leave a flag untouched.
- Fixed a required boolean field being accepted when omitted and sent as `null`; it is now required up front, and its default shows in `--help`.

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
