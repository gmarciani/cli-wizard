# My Cli

A CLI application

## Installation

```bash
pip install -e .
```

## Usage

```bash
my-cli --help
```

## Configuration

Settings live in named profiles, listed by `my-cli config show` and
changed with `my-cli config set --param baseUrl --value <url>`. Each is
resolved through four layers, highest precedence first:

1. The command-line flag, for the settings that have one (`--base-url`).
2. The environment variable `MY_CLI_<SETTING>`, the setting
   name in upper snake case: `baseUrl` reads `MY_CLI_BASE_URL`.
3. The value stored in the profile selected with `--profile`, or `default`.
4. The built-in default.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
