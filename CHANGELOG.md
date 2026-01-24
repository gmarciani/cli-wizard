# Changelog

All notable changes to CLI Wizard will be documented in this file.

## 2.0.0

### Highlights
In this release we finalized the configuration schema, finalized the functionality fo the command `generate` and introduced the new command `bootstrap`.

### Commands

- `cli-wizard bootstrap` - Bootstrap a new CLI project.
                           You will be guided through a step by step procedure to generate
                           a basic CLI and an extensible configuration file to evolve it.
                           No OpenAPI file is required.

- `cli-wizard generate` - Generate a CLI from a configuration file and optional OpenAPI spec.
                          If `--api` is provided, API commands will be generated from the OpenAPI spec.
                          Otherwise, a functional CLI is generated without API commands.

### Configuration Schema

The `cli-wizard.yaml` configuration file supports the following parameters.
All parameters use PascalCase naming convention.
Reference other parameters with `#[ParamName]` syntax.
Reference environment variables with `${VAR}` syntax.

#### Project

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ProjectName` | string | `"My Project"` | Human-readable project name (title case) |
| `CommandName` | string | `"my-project"` | CLI command name (kebab-case) |
| `PackageName` | string | `"my_project"` | Python package name (snake_case) |
| `Description` | string | `"A CLI application"` | Project description |
| `Version` | string | `"1.0.0"` | Project version |
| `PythonVersion` | string | `"3.12"` | Minimum Python version |

#### Author

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `AuthorName` | string | `"Your Name"` | Author name |
| `AuthorEmail` | string | `"your.email@example.com"` | Author email |
| `GithubUser` | string | `"username"` | GitHub username |

#### API

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `DefaultBaseUrl` | string | `"http://localhost:3000"` | Default API base URL |
| `OpenapiSpec` | string | `"openapi.json"` | Path to OpenAPI spec (relative to config file or absolute) |
| `ExcludeTags` | list | `[]` | Tags to exclude from generation |
| `IncludeTags` | list | `[]` | Tags to include (if empty, all non-excluded tags are included) |
| `TagMapping` | dict | `{}` | Map OpenAPI tags to CLI command group names |
| `CommandMapping` | dict | `{}` | Customize command names (operationId -> command name) |

#### API Client

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `Timeout` | integer | `30` | Request timeout in seconds |
| `CaFile` | string \| null | `null` | CA certificate file for SSL verification |
| `RetryMaxAttempts` | integer | `3` | Retry max attempts |
| `RetryBackoffFactor` | float | `0.5` | Retry backoff factor |

#### CLI Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MainDir` | string | `"${HOME}/.#[CommandName]"` | Main directory for CLI data (config, cache, logging, etc.) |
| `ProfileFile` | string | `"#[MainDir]/profiles.yaml"` | Path to profiles YAML file |

#### Output Formatting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `OutputFormat` | `"json"` \| `"table"` \| `"yaml"` | `"json"` | Default output format |
| `OutputColors` | boolean | `true` | Enable colored output |
| `JsonIndent` | integer | `2` | JSON indentation |
| `TableStyle` | `"ascii"` \| `"rounded"` \| `"minimal"` \| `"markdown"` | `"rounded"` | Table style |

#### Splash Screen

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SplashFile` | string \| null | `null` | Path to splash text file (relative to config or absolute) |
| `SplashColor` | string | `"#FFFFFF"` | Color for splash text (hex code) |

#### Logging

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LogLevel` | `"DEBUG"` \| `"INFO"` \| `"WARNING"` \| `"ERROR"` | `"INFO"` | Default log level |
| `LogFormat` | string | `"%(asctime)s [%(levelname)s] %(message)s"` | Log message format (Python logging format) |
| `LogTimestampFormat` | string | `"%Y-%m-%dT%H:%M:%S"` | Timestamp format for log messages (strftime format) |
| `LogTimezone` | `"UTC"` \| `"Local"` | `"UTC"` | Timezone for log timestamps |
| `LogColorStyle` | `"full"` \| `"level"` | `"level"` | Log color style |
| `LogColorDebug` | string | `"#808080"` | Color for DEBUG log level (hex code) |
| `LogColorInfo` | string | `"#00FF00"` | Color for INFO log level (hex code) |
| `LogColorWarning` | string | `"#FFFF00"` | Color for WARNING log level (hex code) |
| `LogColorError` | string | `"#FF0000"` | Color for ERROR log level (hex code) |
| `LogFile` | string \| null | `null` | Path to log file (null means no file logging) |
| `LogRotationType` | `"size"` \| `"days"` | `"days"` | Log rotation type |
| `LogRotationSize` | integer | `10` | Log rotation size in MB (when LogRotationType is 'size') |
| `LogRotationDays` | integer | `30` | Log rotation interval in days (when LogRotationType is 'days') |
| `LogRotationBackupCount` | integer | `5` | Number of backup log files to keep |

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
