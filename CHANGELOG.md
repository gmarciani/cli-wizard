# Changelog

All notable changes to CLI Wizard will be documented in this file.

## 1.0.0

🎉 **Initial Release**

CLI Wizard transforms your OpenAPI specifications into customizable Python CLIs powered by the Click framework.

### Features

**Code Generation**
- Generate complete Python CLI projects from OpenAPI v3 specifications
- Automatic command grouping based on OpenAPI tags
- Automatic helper generation for all commands
- Clean, colored terminal output
- `--debug` flag for verbose logging
- Built-in API client with configurable base URL and timeout
- SSL/TLS support with custom CA certificate bundles
- `--ca-file` option to specify custom CA certificates at runtime
- `--no-verify-ssl` flag to disable certificate verification

**Customizations**
- YAML-based configuration for full customization
- Configurable output directory and package name
- Tag inclusion/exclusion filters
- Custom command naming via `tag_mapping` and `command_mapping`
- Customizable tag-to-command mapping
- Customizable operation-to-command name mapping
- Customizable splash screen with color support

**Developer Experience**
- Generated projects are pip-installable out of the box
- Auto-generated `pyproject.toml`, `README.md`, and `VERSION`
- Resources (CA certs, splash files) bundled in the package

### Commands

- `cli-wizard generate` - Generate a CLI from OpenAPI spec and config file
