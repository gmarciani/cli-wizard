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
cli-wizard generate examples/my-cli --configuration examples/cli-wizard.yaml --api examples/openapi.json
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
`MainDir: "${HOME}/.#[CommandName]"`. Resolved by `_expand_config_references()`,
duplicated in `commands/generate.py` and `commands/bootstrap.py` — keep both in
sync. `${VAR}` is deliberately left alone; the generated CLI expands it at
runtime.

**Pipeline** (`parser.py` → `models.py` → `generator.py`). `OpenApiParser.parse()`
groups operations by tag into `CommandGroup`s, applying the include/exclude
filters. `models.py` dataclasses expose the name conversions templates rely on
(`param.cli_name`, `op.function_name`). `CliGenerator.generate()` writes the
tree, resolves resource paths relative to the *config file's* directory, renders
the templates, then formats.

**Templates** in `src/cli_wizard/templates/` mirror the output layout. The
literal `{{ PackageName }}` directory name is resolved by string substitution,
not by Jinja. Files needing the package name must be `.j2` and rendered;
anything in the generator's `static_files` list is copied byte-for-byte, so it
cannot reference the generated project.

**Debug output is redacted, never raw.** Every payload a generated CLI logs —
command parameters, request params and body, response body, request and
response headers — passes through the generated `redaction.py`. Spec signals
(`format: password`, `writeOnly`) are collected once by `_sensitive_field_names()`
and baked into that module as a project-wide constant, deliberately rather than
threaded per-operation through the client and every command. The name heuristic
next to it covers what no spec describes, response bodies above all. Redact
*before* truncating: half a token is still a token.

## Formatting

Ruff is the only formatter and linter, for this repo and for generated code,
under identical settings (line-length 88, `select = ["E", "F", "W", "I"]`, no
ignores) in `pyproject.toml` and `templates/pyproject.toml.j2` — keep the two in
sync. Ruff is a runtime dependency and `resolve_ruff()` prefers the bundled copy
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
