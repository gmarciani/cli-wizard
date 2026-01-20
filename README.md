# CLI WIZARD

<div align="center">
<img src="resources/brand/logo.png" alt="cli-wizard-logo" width="500">

[![PyPI version](https://img.shields.io/pypi/v/cli-wizard.svg)](https://pypi.org/project/cli-wizard/)
[![Python versions](https://img.shields.io/pypi/pyversions/cli-wizard.svg)](https://pypi.org/project/cli-wizard/)
[![License](https://img.shields.io/github/license/gmarciani/cli-wizard.svg)](https://github.com/gmarciani/cli-wizard/blob/main/LICENSE)
[![Build status](https://img.shields.io/github/actions/workflow/status/gmarciani/cli-wizard/test.yml?branch=main)](https://github.com/gmarciani/cli-wizard/actions)
[![Tests](https://img.shields.io/github/actions/workflow/status/gmarciani/cli-wizard/test.yml?branch=main&label=tests)](https://github.com/gmarciani/cli-wizard/actions)
[![Coverage](https://img.shields.io/codecov/c/github/gmarciani/cli-wizard)](https://codecov.io/gh/gmarciani/cli-wizard)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Downloads](https://img.shields.io/pypi/dm/cli-wizard.svg)](https://pypi.org/project/cli-wizard/)

</div>

Generate modern CLIs from OpenAPI specifications.

<div align="center">
<img src="resources/brand/demo.mp4.gif" alt="cli-wizard-demo" width="800">
</div>

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Commands](#commands)
- [Issues](#issues)
- [License](#license)

## Features

### Code Generation
- Generate complete Python CLI projects from OpenAPI v3 specifications
- Automatic command grouping based on OpenAPI tags
- Automatic help generation for all commands
- Clean, colored terminal output
- `--debug` flag for verbose logging
- Built-in API client with configurable base URL and timeout
- SSL/TLS support with custom CA certificate bundles
- `--ca-file` option to specify custom CA certificates at runtime
- `--no-verify-ssl` flag to disable certificate verification

### Customization
- YAML-based configuration for full customization
- Configurable output directory and package name
- Tag inclusion/exclusion filters
- Custom command naming via `TagMapping` and `CommandMapping`
- Customizable splash screen with color support
- Configurable logging with colors, file output, and rotation

### Developer Experience
- Generated projects are pip-installable out of the box
- Auto-generated `pyproject.toml`, `README.md`, and `VERSION`
- Resources (CA certs, splash files) bundled in the package
- Profile management for storing credentials and settings

## Installation

```shell
pip install cli-wizard
```

## Usage

### Step 1: Prepare Your OpenAPI Specification

Ensure you have an OpenAPI v3 specification file (JSON or YAML format). For example, `openapi.yaml`:

```yaml
openapi: 3.0.0
info:
  title: My API
  version: 1.0.0
paths:
  /users:
    get:
      operationId: listUsers
      summary: List all users
      tags:
        - Users
      responses:
        '200':
          description: OK
```

### Step 2: Create a Configuration File

Create a `config.yaml` file with your CLI settings. At minimum, you need `PackageName` and `DefaultBaseUrl`:

```yaml
# Required parameters
PackageName: "my-cli"
DefaultBaseUrl: "https://api.example.com"

# Optional: customize the splash screen
SplashFile: "splash.txt"
SplashColor: "#00FFFF"

# Optional: filter which tags to include
IncludeTags:
  - Users
  - Products
```

### Step 3: Generate the CLI

Run the `generate` command:

```shell
cli-wizard generate --openapi openapi.yaml --config config.yaml --output my-cli
```

This creates a complete Python CLI project in the `my-cli` directory.

### Step 4: Install the Generated CLI

Navigate to the generated project and install it:

```shell
pip install -e my-cli
```

### Step 5: Use Your CLI

Your CLI is now ready to use:

```shell
my-cli --help
my-cli users list-users
```

## Configuration

Configuration uses a YAML file with PascalCase parameter names. You can reference other parameters with `#[ParamName]` syntax and environment variables with `${VAR}` syntax.

### Required Parameters

| Parameter | Description |
|-----------|-------------|
| `PackageName` | Python package name for the generated CLI |
| `DefaultBaseUrl` | Default API base URL |

### Common Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OutputDir` | `#[PackageName]` | Output directory for the generated CLI project |
| `MainDir` | `${HOME}/.#[PackageName]` | Main directory for CLI data (config, cache, logs) |
| `ProfileFile` | `#[MainDir]/profiles.yaml` | Path to profiles YAML file |
| `ExcludeTags` | `[]` | Tags to exclude from generation |
| `IncludeTags` | `[]` | Tags to include (empty means all) |
| `TagMapping` | `{}` | Map OpenAPI tags to CLI command group names |
| `CommandMapping` | `{}` | Customize command names (operationId → command name) |
| `SplashFile` | `None` | Path to splash text file |
| `SplashColor` | `#FFFFFF` | Color for splash text (hex code) |
| `Timeout` | `30` | Request timeout in seconds |
| `CaFile` | `None` | CA certificate file for SSL verification |

### Logging Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LogLevel` | `INFO` | Default log level (DEBUG, INFO, WARNING, ERROR) |
| `LogFormat` | `[%(levelname)s] %(asctime)s %(message)s` | Log message format |
| `LogFile` | `None` | Path to log file (None means console only) |
| `LogRotationType` | `days` | Log rotation type: `size` or `days` |
| `LogRotationDays` | `30` | Log rotation interval in days |
| `LogColorStyle` | `level` | Color style: `full` or `level` |

See the [examples](examples/) directory for complete configuration examples.

## Commands

### cli-wizard generate

Generate a CLI from an OpenAPI specification and configuration file.

```shell
cli-wizard generate [OPTIONS]
```

Options:
- `--openapi, -o` - Path to OpenAPI spec file (default: `openapi.yaml`)
- `--config, -c` - Path to config YAML file (default: `config.yaml`)
- `--output, -d` - Output directory for generated CLI (default: `cli`)
- `--working-dir, -w` - Working directory for resolving relative paths

## Issues

Please report any issues or feature requests on the [GitHub Issues](https://github.com/gmarciani/cli-wizard/issues) page.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
