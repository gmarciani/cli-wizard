# Changelog

All notable changes will be documented in this file.

## 1.0.0

🎉 **Initial Release**

A CLI application

### Features

Add features here ...

### Commands

- `my-cli config` - Configure the CLI.
  - `my-cli config init` - Initialize the profile file with default profile.
  - `my-cli config list-profiles` - List all available profiles.
  - `my-cli config show` - Show all parameters and values for a profile.
  - `my-cli config get` - Get a configuration value from a profile.
  - `my-cli config set` - Set a configuration value in a profile.
  - `my-cli config unset` - Remove a configuration value from a profile.
- `my-cli private` - Private commands
  - `my-cli private get-greetings` - Get a greeting message (authenticated)
- `my-cli public` - Public commands
  - `my-cli public get-public-greetings` - Get a public greeting message
- `my-cli --help` - Prints the helper.
- `my-cli --version` - Prints the version.
