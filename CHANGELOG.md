# Changelog

All notable changes to CLI Wizard will be documented in this file.

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
