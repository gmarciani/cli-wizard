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

Generate modern CLI from OpenAPI

<div align="center">
<img src="resources/brand/demo.mp4.gif" alt="cli-wizard-demo" width="800">
</div>

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Issues](#issues)
- [License](#license)

## Features

### Code Generation
- Generate complete Python CLI projects from OpenAPI v3 specifications
- Automatic command grouping based on OpenAPI tags
- Automatic helper generation for all commands
- Clean, colored terminal output
- `--debug` flag for verbose logging
- Built-in API client with configurable base URL and timeout
- SSL/TLS support with custom CA certificate bundles
- `--ca-file` option to specify custom CA certificates at runtime
- `--no-verify-ssl` flag to disable certificate verification

### Customizations
- YAML-based configuration for full customization
- Configurable output directory and package name
- Tag inclusion/exclusion filters
- Custom command naming via `tag_mapping` and `command_mapping`
- Customizable tag-to-command mapping
- Customizable operation-to-command name mapping
- Customizable splash screen with color support

### Developer Experience
- Generated projects are pip-installable out of the box
- Auto-generated `pyproject.toml`, `README.md`, and `VERSION`
- Resources (CA certs, splash files) bundled in the package

## Installation

```shell
pip install cli-wizard
```

## Usage

## Issues

Please report any issues or feature requests on the [GitHub Issues](https://github.com/gmarciani/cli-wizard/issues) page.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
