# My Cli

A CLI application

## Installation

```bash
pip install -e .
```

## Quick start

Create the profile file, point the CLI at the API and store the token it
authenticates with:

```bash
my-cli config init
my-cli config set --param baseUrl --value http://localhost:3000
my-cli config set --param accessToken --value <token>
```

Then run a command, or ask any command for its options with `--help`:

```bash
my-cli private get-greetings --help
```

The base URL defaults to `http://localhost:3000`, so the second line
is only needed to reach another host. See [Configuration](#configuration) and
[Authentication](#authentication) for the details.

## Commands

- [config get](#config-get)
- [config init](#config-init)
- [config list-profiles](#config-list-profiles)
- [config set](#config-set)
- [config show](#config-show)
- [config unset](#config-unset)
- [private get-greetings](#private-get-greetings)
- [public get-public-greetings](#public-get-public-greetings)

### Common Options

Every command takes these options, which also apply to every command when given
right after `my-cli` or after a group name:

- `--profile`, `-p` - Profile to read settings from. Default: `default`.
- `--base-url`, `-u` - API base URL, overriding the profile and the environment.
- `--ca-file` - CA certificate bundle to verify the server against.
- `--no-verify-ssl` - Disable TLS certificate verification. Prints a warning.
- `--timeout` - Seconds to wait for a response, overriding the `timeout` setting.
- `--header`, `-H` - Extra request header as `Name: value`. Repeatable.
- `--output`, `-o` - Print the response as `json`, `yaml` or `table`, overriding
  the `outputFormat` setting.
- `--debug`, `-d` - Log the request and response, with credentials redacted.
- `--help` - Show the options of the command.

`my-cli --version` prints the version.

### Exit codes

Every command prints one JSON document on stdout: the response on success, or
on failure an error object a script can parse, with the error's type, its
message and the exit code the command exits with:

```json
{
  "error": {
    "type": "ClientError",
    "message": "404 Not Found\n  Greeting not found",
    "exitCode": 4
  }
}
```

Logs go to stderr. The exit code names the class of what went wrong, so a
script can branch on it or retry only what is worth retrying.

| Code | Meaning |
|---|---|
| 0 | The command succeeded. |
| 1 | Any other failure. |
| 2 | Usage error: an unknown command, a missing option or a bad value. |
| 3 | No response: connection refused, unknown host, timeout or TLS failure. |
| 4 | The API rejected the request, with a 4xx, or a `--header` is not `Name: value`. |
| 5 | The API failed, with a 5xx. |
| 6 | The response body is not valid JSON. |
| 7 | The profile file cannot be read or written, the selected profile is not in it, or a configured file does not exist. |
| 8 | A bug in the CLI; `--debug` logs its traceback. |

### config

Configure the CLI.

#### config get

Get a configuration value from a profile.

- `--param TEXT` (required) - Parameter name.

#### config init

Initialize the profile file with default profile.

#### config list-profiles

List all available profiles.

#### config set

Set a configuration value in a profile.

- `--param TEXT` (required) - Parameter name.
- `--value TEXT` (required) - Parameter value.

#### config show

Show all parameters and values for a profile.

#### config unset

Remove a configuration value from a profile.

- `--param TEXT` (required) - Parameter name.

### private

Private commands

#### private get-greetings

Get a greeting message (authenticated)

### public

Public commands

#### public get-public-greetings

Get a public greeting message

## Configuration

Settings live in named profiles in `${HOME}/.my-cli/profiles.yaml`. `my-cli config init`
creates the file with an empty `default` profile, and any command creates it on
first run if it is missing. `my-cli config show` lists a profile with the
defaults filled in, `my-cli config set --param <setting> --value <value>`
changes one setting and `--profile <name>` on any command selects a profile other
than `default`. An API command given a profile the file does not hold fails
without sending the request; `config set --profile <name>` creates it.

| Setting | Default | Effect |
|---|---|---|
| `baseUrl` | `http://localhost:3000` | Base URL of the API every command sends its requests to. |
| `accessToken` | unset | Bearer token sent in the `Authorization` header of every request. |
| `timeout` | `30` | Seconds to wait for a response before a request fails. |
| `outputFormat` | `json` | How a command prints the response: `json`, `yaml` or `table`. `--output` overrides it for one invocation. |
| `jsonIndent` | `2` | Indentation of the JSON a command prints. |
| `tableStyle` | `rounded` | Borders of a `table` output: `rounded`, `ascii`, `minimal` or `markdown`. |
| `logLevel` | `INFO` | Lowest level of log message shown: DEBUG, INFO, WARNING or ERROR. |
| `outputColors` | `true` | Whether log messages and errors are coloured. |
| `retryMaxAttempts` | `3` | Retries of a request that could not connect or got a 429 or 5xx response, after the first attempt. `0` sends every request once. |
| `retryBackoffFactor` | `0.5` | Seconds waited before retry *n*: the factor times 2^(n-1), or what a `Retry-After` header asks. |

Each setting is resolved through four layers, highest precedence first:

1. The command-line flag, for the settings that have one (`--base-url`,
   `--timeout`, `--output`).
2. The environment variable `MY_CLI_<SETTING>`, the setting
   name in upper snake case: `baseUrl` reads `MY_CLI_BASE_URL`.
3. The value stored in the profile selected with `--profile`, or `default`.
4. The built-in default.

## Authentication

Requests are authenticated with a bearer token: when `accessToken` is set, every
request carries an `Authorization: Bearer <token>` header. Without it, requests
are sent anonymously. Obtaining the token is up to the API; once you have it,
store it in the profile:

```bash
my-cli config set --param accessToken --value <token>
```

or hand it to a single invocation through the environment:

```bash
MY_CLI_ACCESS_TOKEN=<token> my-cli private get-greetings
```

The profile file is created readable by its owner only, and `--debug` output
redacts the token.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
