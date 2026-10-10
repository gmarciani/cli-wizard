# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

CLI Wizard generates pip-installable Click CLI projects from an OpenAPI v3 spec
plus a `cli-wizard.yaml` config. `bootstrap` scaffolds interactively without a
spec; `generate` builds or rebuilds from one. The output is a full Python
project rendered from Jinja2 templates.

## Commands

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, tox environments, docs and
releases. Not covered there:

```shell
# Single test, faster than tox while iterating
pytest tests/cli_wizard/generator/generator_test.py::TestBuildUrlPath -v

# End-to-end against the bundled example
cli-wizard generate --configuration examples/cli-wizard.yaml --api examples/openapi.json \
  --output examples/my-cli --force
```

## Architecture

**Two unrelated config systems, easy to conflate.** `~/.cli_wizard/cli-wizard.yaml`
is the tool's own key-value settings (`commands/config.py`). A project-level
`cli-wizard.yaml` is the generation config validated against the Pydantic
`Config` in `config/schema.py` — that one drives the generator.

**`config/schema.py` is the single source of truth.** Each parameter is one
Pydantic `Field`, and that definition feeds config validation, the commented
example written by `bootstrap`, and the Jinja context (templates write
`{{ ProjectName }}`, not `{{ config.ProjectName }}`). Adding a parameter means
adding one `Field`; add it to `BOOTSTRAP_PARAMS` too if it should be prompted.
Derivations belong here rather than in the bootstrap prompts, so `generate`
gets them as well.

**`#[Param]` expansion.** Config values may reference others, e.g.
`MainDir: "${HOME}/.#[CommandName]"`. Resolved by `expand_config_references()`
in `config/project.py`, which `load_cli_config()` applies for both `generate`
and `bootstrap`. `${VAR}` is deliberately left alone; the generated CLI expands
it at runtime.

**Pipeline** (`parser.py` → `models.py` → `generator.py`). `OpenApiParser.parse()`
groups operations by tag into `CommandGroup`s, applying the include/exclude
filters. `models.py` dataclasses expose the name conversions templates rely on
(`param.cli_name`, `op.function_name`). `CliGenerator.generate()` writes the
tree, resolves resource paths relative to the *config file's* directory, renders
the templates, then formats.

**Templates** in `src/cli_wizard/templates/` mirror the output layout. The
literal `{{ PackageName }}` directory name is resolved by string substitution,
not by Jinja. `CliGenerator._render()` renders every template with the shared
context; the ones needing nothing else are listed in `PLAIN_TEMPLATES` and
`GITHUB_TEMPLATES`, the rest get their extra context in `generate()`. Files
needing the package name must be `.j2` and rendered; anything in `STATIC_FILES`
is copied byte-for-byte, so it cannot reference the generated project.

**Generated modules share, never repeat.** The invocation state lives in the
generated `state.py`, which depends on the constants alone, so every module
reads it from there. The profiles file is read and written by `read_profiles()`
and `write_profiles()` in `profile.py`, the client sends every verb through
`_send()`, and `runner.run_command()` carries what every API command does: the
settings, the request, the error classes and the output. A command module only
builds its parameters and hands the runner a lambda that sends the request.

**Debug output is redacted, never raw.** Every payload a generated CLI logs —
command parameters, request params and body, response body, request and
response headers — passes through the generated `redaction.py`. Spec signals
(`format: password`, `writeOnly`) are collected once by `_sensitive_field_names()`
and baked into that module as a project-wide constant, deliberately rather than
threaded per-operation through the client and every command. The name heuristic
next to it covers what no spec describes, response bodies above all. Redact
*before* truncating: half a token is still a token.

**stdout is one JSON document, errors included.** Both CLIs print their result
as JSON on stdout and everything else, progress, prompts, hints and logs, on
stderr. A failure is `{"error": {"type", "message", "exitCode"}}` on stdout,
printed by the error's `show()`. cli-wizard raises the `CliWizardError`
subclasses in `errors.py`; generated code raises the `CliError` subclasses in
the generated `errors.py`. Every class has its own exit code, a class attribute
(Click declares `exit_code` a `ClassVar`); 1 is the base, raised only for a Click
error that is not about usage, and 2 stays Click's usage error. Both are
`click.ClickException`s, so Click shows them and exits with their code, but no
code raises a Click class, `SystemExit` or
`self.fail()`, and `click.confirm(abort=True)` is replaced by raising `Aborted`;
`TestOnlyProjectErrorsAreRaised` scans the sources and templates for those
patterns. What Click raises on its own, a bad option or an unknown command, and
any unexpected exception are wrapped by `reported()` in `RootGroup.make_context`
and `invoke`, the one choke point inside Click's `main()`, into `UsageError` and
`UnexpectedError`; the traceback goes to the debug log there. A generated
command catches `requests.RequestException` only and raises the matching
`RequestError` subclass. The JSON decode sits outside that `try`, so
a malformed 200 body is a `ResponseError`, not a failed request. Log the failure
*before* raising: by the time Click shows the error, the context, and with it
the logger and the profile settings, is gone, which is also why `CliError`
captures the JSON indentation in its constructor. The generated `errors.py` sits
below `options.py`, which raises `ClientError` for a bad `--header`, so it
imports nothing above `state.py`.

## Formatting

Ruff is the only formatter and linter, for this repo and for generated code,
under identical settings (line-length 88, `select = ["E", "F", "W", "I", "B",
"S", "UP"]` with `S101` ignored under `tests/`, no other ignores) in `pyproject.toml`
and `templates/pyproject.toml.j2` — keep the two in sync. Ruff is a runtime dependency and `resolve_ruff()` prefers the bundled copy
over `PATH`, so the pinned version formats. Nothing passes `--line-length`; ruff
reads it from the generated `pyproject.toml`.

`RUFF_COMMANDS` mirrors `[testenv:format]` in `templates/tox.ini.j2`;
`test_format_recipe_matches_tox_template` fails if they drift. `--no-cache` is
generator-side only, outside `RUFF_COMMANDS`, or ruff leaves a `.ruff_cache`
behind.

Invariants, each learned from a real bug:

- Formatting is never best-effort; skipping it silently shipped hundreds of
  lines of diff churn per regeneration.
- Resolve ruff *before* `commands/generate.py` deletes the previous output, or a
  failure destroys the user's work and then aborts.
- Ruff exit 1 (violations remain) warrants a warning; exit 2 (could not run,
  including unparseable output) is fatal.

## Testing conventions

`tests/` mirrors `src/cli_wizard/`, using `TestX` classes with `test_*` methods.
`examples/` is fixture data and an end-to-end reference, not a package under
test; regenerating it must produce no diff.
