# CLI Wizard — Roadmap

> Usage, configuration reference, and the command list live in [README.md](README.md). Environment setup and the release procedure live in [DEVELOPMENT.md](DEVELOPMENT.md).

A single prioritized list of **stories**, ordered by severity: data loss and unrecoverable states first, then defects that produce a broken generated CLI, then correctness and housekeeping. Every story was reproduced against v2.1.0 before being written down.

Every story is tagged by type in its title: **[F]** feature · **[B]** bug fix · **[O]** operational.

## Overview

| # | Status | Story | Summary |
|---|---|---|---|
| **S1**  |    | [B] `generate` deletes the output directory without asking | Confirm before destroying an existing directory, as `bootstrap` already does |
| **S2**  |    | [B] Circular `#[Param]` references hang forever | Bound the expansion and fail loudly instead of looping |
| **S3**  |    | [B] `config set` bricks the tool with no way back | Validate on write, degrade on read, make `reset` always work |
| **S4**  |    | [B] `bootstrap` writes YAML it cannot read back | Escape scalars so quotes and backslashes survive the round trip |
| **S5**  |    | [B] The README documents a CLI that does not exist | Correct the command reference to the flags the tool actually has |
| **S6**  |    | [B] `$ref` parameters crash the parser | Resolve component references before reading parameter fields |
| **S7**  |    | [B] Path-level parameters are silently dropped | Merge path-level `parameters` into every operation on that path |
| **S8**  |    | [B] Acronyms are mangled into per-letter names | One acronym-aware converter for commands, params, and body properties |
| **S9**  |    | [B] Derived `PackageName` can be an invalid identifier | Reject package names Python cannot import |
| **S10** |    | [B] `get_field_default` returns the Pydantic sentinel | Honour `default_factory` instead of leaking `PydanticUndefined` |
| **S11** |    | [B] Missing `CaFile` / `SplashFile` fail silently | Warn instead of generating a CLI with no CA configured |
| **S12** |    | [B] `CopyrightYear` renders as `None` in LICENSE | Default the year rather than emitting a literal `None` |
| **S13** |    | [B] `IncludeOperations` does not filter | Make the whitelist behave as its own description promises |
| **S14** |    | [O] Single-source the `#[Param]` expander | One implementation instead of two copies kept in sync by hand |
| **S15** |    | [O] Dead code cleanup | Remove unreachable branches and an unused template override |
| **S16** |    | [O] Initialize `CliGenerator` state in the constructor | Close a latent `AttributeError` on direct method calls |
| **S17** |    | [O] Make the test suite resolve the package under test | Stop an editable install from silently testing another checkout |

---

## Stories

### S1 — [B] `generate` deletes the output directory without asking
`commands/generate.py:137` calls `shutil.rmtree(output_path)` unconditionally on any directory that already exists. The only guard, at lines 120–134, checks whether the user is standing *inside* that directory — it does nothing for a directory that merely holds work. Pointing `generate` at an existing project removes everything in it, `.git` included, with no prompt and no flag to opt out. `bootstrap` already prompts before touching a non-empty directory; `generate` is the more destructive of the two and asks nothing.

**Acceptance criteria**
- `generate` refuses to delete a non-empty output directory without either an interactive confirmation or an explicit `--force` / `-f` flag.
- The confirmation names the directory and states that its entire contents will be deleted.
- Declining leaves the directory untouched and exits non-zero.
- An empty or non-existent output directory proceeds without prompting.
- The existing "cannot clean while inside it" guard is preserved.

### S2 — [B] Circular `#[Param]` references hang forever
`_expand_config_references` loops `while prev_value != value`, re-substituting a reference that still contains itself, so it never converges. A self-reference such as `MainDir: "#[MainDir]/x"` grows the string without bound until memory is exhausted; a mutual pair such as `A: "#[B]"` / `B: "#[A]"` oscillates between two values forever. Both were observed hanging past a 5-second timeout and had to be killed. `MainDir` is user-editable and its schema default already contains a reference, so an ordinary config typo reaches this. The logic is duplicated in `commands/generate.py:199-217` and `commands/bootstrap.py:330-347`; both copies have the defect.

**Acceptance criteria**
- Expansion terminates on any input, including direct self-references and mutual cycles.
- A reference that cannot be resolved raises a clear error naming the offending value, instead of hanging.
- A value whose replacement still contains its own reference is left unexpanded rather than substituted into itself.
- Legitimate nested references (`MainDir` → `ProfileFile`) still resolve fully.
- Both copies of the expander behave identically.

### S3 — [B] `config set` bricks the tool with no way back
`commands/config.py:26-34` writes any key and value straight to disk without validating either. `config/configuration.py:37` then catches only `(yaml.YAMLError, IOError)`, so the `ValidationError` raised by the `extra: "forbid"` schema propagates as an uncaught traceback on the next read. Because `reset` calls `load_config()` at line 77 *before* unlinking the file, the documented recovery path fails too — the tool locks itself out permanently and only manual deletion of `~/.cli_wizard/cli-wizard.yaml` restores it. Observed:

```
1. config set foo bar        -> exit 0   (accepted)
2. config show               -> exit 1, ValidationError
3. config get ProjectName    -> exit 1, ValidationError
4. config reset  (recovery!) -> exit 1, ValidationError
```

Three routes reach this state: an unknown key, `config unset` on a non-optional field, and a value of the wrong type (`config set JsonIndent abc`).

**Acceptance criteria**
- `config set` rejects unknown keys with a clear message and a non-zero exit, writing nothing.
- `config set` validates and coerces the value against the schema before saving; an invalid value is rejected without modifying the stored config.
- `config unset` refuses fields that are not optional in the schema.
- `load_config` treats an invalid or corrupt config file the same way it treats unreadable YAML: warn and fall back to schema defaults.
- `config reset` succeeds regardless of the state of the existing file, and does not read it first.
- Regression tests cover all three corruption routes and confirm `reset` recovers from each.

### S4 — [B] `bootstrap` writes YAML it cannot read back
`_yaml_value` (`commands/bootstrap.py:249-273`) wraps every string in double quotes but escapes nothing inside them, so any value containing a quote or a backslash produces a file that fails to parse. `bootstrap` reloads the file it just wrote at line 215, so the command breaks on its own output:

| Prompted value | Written as | Reload |
|---|---|---|
| `My "cool" CLI` | `"My "cool" CLI"` | `ParserError` |
| `C:\path\to` | `"C:\path\to"` | `ScannerError` |

A description containing a quotation mark or any Windows-style path is enough. All three branches of the function also return the identical expression, so the two `if` statements are unreachable-equivalent.

**Acceptance criteria**
- Every value accepted at a bootstrap prompt round-trips through the generated `cli-wizard.yaml` unchanged.
- Quotes, backslashes, colons, and leading/trailing whitespace are escaped correctly.
- `null`, booleans, numbers, lists, and dicts keep their current YAML rendering.
- The unreachable branches are removed.
- Regression tests assert round-trip equality for a set of hostile string values.

### S5 — [B] The README documents a CLI that does not exist
The `## Commands` section of `README.md` documents four options for `generate` — `--openapi/-o`, `--config/-c`, `--output/-d`, `--working-dir/-w` — none of which the command accepts. The real signature is `generate [OPTIONS] PATH` with `--configuration/-c` and `--api/-a`; the required positional `PATH` is not mentioned at all. Every invocation copied from that section fails. `bootstrap` and `config`, both shipped and both listed in `--help`, are absent from the section entirely.

**Acceptance criteria**
- The documented options for `generate` match `cli-wizard generate --help` exactly, including the required positional `PATH`.
- `bootstrap` and `config` are documented with their real options and subcommands.
- Every command example in the README runs successfully as written against a clean checkout.
- The Table of Contents covers any section added.

### S6 — [B] `$ref` parameters crash the parser
`_parse_parameter` (`generator/parser.py:140-151`) reads `param["name"]` directly, so a parameter given as `{"$ref": "#/components/parameters/Verbose"}` raises `KeyError('name')`. Component-level parameter reuse is ordinary OpenAPI, so cli-wizard rejects valid specs outright. `_resolve_ref` (lines 181–189) additionally hardcodes the `schemas` section, so it cannot resolve a parameter reference even when called.

**Acceptance criteria**
- A parameter expressed as a `$ref` is resolved and parsed like an inline one.
- `_resolve_ref` resolves any `#/components/<section>/<name>` pointer, not only `schemas`.
- An unresolvable `$ref` produces a clear error naming the pointer, not a `KeyError`.
- A spec mixing inline and `$ref` parameters on the same operation parses correctly.

### S7 — [B] Path-level parameters are silently dropped
`generator/parser.py:66-67` iterates `path_item.items()` and skips every key that is not an HTTP method, which discards the sibling `parameters` key. OpenAPI defines those as applying to every operation under that path, and declaring shared path parameters there is the idiomatic form. The failure is silent and produces a broken CLI: the generated command exposes no option for the parameter, and the URL keeps its literal placeholder. Observed on a path declaring `thingId` at path level — `op.parameters` came back empty and the URL rendered as `/things/{thingId}`.

**Acceptance criteria**
- Path-level `parameters` are parsed and applied to every operation under that path.
- An operation-level parameter overrides a path-level one with the same name and location.
- Path-level `$ref` parameters resolve (depends on S6).
- The generated command exposes the corresponding option and the URL placeholder is substituted.

### S8 — [B] Acronyms are mangled into per-letter names
`Operation.command_name` (`generator/models.py:102`) inserts a dash before every capital letter, so acronyms explode into single characters. These names are user-facing commands and also become the generated Python function names:

| `operationId` | Current | Expected |
|---|---|---|
| `listAPIKeys` | `list-a-p-i-keys` | `list-api-keys` |
| `getHTTPStatus` | `get-h-t-t-p-status` | `get-http-status` |
| `getUserByID` | `get-user-by-i-d` | `get-user-by-id` |

`Parameter.cli_name` (line 26) and `RequestBodyProperty.cli_name` (line 58) use a different regex with the opposite failure — they collapse acronyms entirely, turning `APIKey` into `apikey` and `XMLData` into `xmldata`. Three near-duplicate conversions with two distinct bugs.

**Acceptance criteria**
- A single shared converter handles operation IDs, parameter names, and body property names.
- Acronyms convert as whole words: `listAPIKeys` → `list-api-keys`, `APIKey` → `api-key`.
- Existing correct conversions (`get_user` → `get-user`, `userID` → `user-id`) are unchanged.
- Python names derive from the CLI names and remain valid identifiers.
- Parameterized regression tests cover camelCase, snake_case, leading acronyms, trailing acronyms, and mixed forms.

### S9 — [B] Derived `PackageName` can be an invalid identifier
`config/schema.py:252-255` derives `PackageName` by replacing non-alphanumerics with underscores, but never guards against a leading digit. `ProjectName: "2FA Tool"` yields `2fa_tool` and `ProjectName: "123"` yields `123` — neither is importable, so the generated project fails at `pip install -e .` with no earlier warning.

**Acceptance criteria**
- A derived or explicitly configured `PackageName` that is not a valid Python identifier is rejected at config validation time.
- The error names the offending value and states the constraint.
- The same validation applies whether the name was derived or supplied directly.
- `CommandName` is validated for the character set a Click command name allows.

### S10 — [B] `get_field_default` returns the Pydantic sentinel
`config/schema.py:290-296` tests `if field_info.default is not None`, but for a field declared with `default_factory` the default is `PydanticUndefined`, not `None` — so the guard passes and the sentinel is returned, leaving the `default_factory` branch unreachable. `Config.get_field_default("IncludeTags")` returns `PydanticUndefined`, which a bootstrap prompt would render as the literal string `"PydanticUndefined"`. Latent only because no collection field currently appears in `BOOTSTRAP_PARAMS`. `get_all_fields_metadata` at line 311 already handles this correctly, so the two accessors disagree.

**Acceptance criteria**
- `get_field_default` returns `[]` for `IncludeTags` and `{}` for `TagMapping`.
- Fields whose default genuinely is `None` still return `None`.
- The sentinel is never returned to a caller.
- Both default accessors share one implementation or are covered by the same tests.

### S11 — [B] Missing `CaFile` / `SplashFile` fail silently
`_copy_ca_file` (`generator/generator.py:248`) and `_copy_splash_file` (line 278) return `None` when the configured path does not resolve, and generation continues as though the option had never been set. A typo in `CaFile` produces a CLI with an empty `resources/` directory and no CA configured — a security-relevant downgrade of TLS trust delivered without a single line of output.

**Acceptance criteria**
- A configured `CaFile` or `SplashFile` that cannot be found produces a visible warning naming the path that was tried, including the directory it was resolved against.
- Generation still completes, so the failure is recoverable.
- Resolving a path that does exist is unchanged.
- Tests assert the warning appears for a missing file and does not for a present one.

### S12 — [B] `CopyrightYear` renders as `None` in LICENSE
`CopyrightYear` defaults to `None` in `config/schema.py:231-234`, and `templates/LICENSE.j2:3` interpolates it unguarded. A config that omits the field — which is every config not produced by `bootstrap`, since only the bootstrap prompt sets it — generates `Copyright (c) None Your Name`.

**Acceptance criteria**
- A config that omits `CopyrightYear` generates a LICENSE carrying the current year.
- An explicitly configured year is still honoured.
- No generated file can contain a literal `None` from an unset optional config field.

### S13 — [B] `IncludeOperations` does not filter
The field's own description reads *"Operation IDs to include (if empty, all non-excluded operations are included)"*, which promises a whitelist when the list is non-empty. `generator/parser.py:77-90` only uses it to *bypass* tag filtering, so listing one operation includes every other one as well:

```
IncludeOperations=['opA']  =>  expected ['opA'], got ['opA', 'opB', 'opC']
```

The current behaviour is documented in `CLAUDE.md`, so the code may be deliberate and the field description wrong — but the two contradict each other and one has to change. Since the project is published, resolving it in favour of the whitelist changes behaviour for anyone relying on today's semantics, and belongs in a major release with a migration note.

**Acceptance criteria**
- A decision is recorded on whether `IncludeOperations` is a whitelist or a tag-filter bypass.
- The code, the field description in `config/schema.py`, the README configuration reference, and `CLAUDE.md` all state the same thing.
- If the whitelist reading wins, a non-empty `IncludeOperations` yields exactly the listed operations, and `ExcludeOperations` still wins over it.
- Any behaviour change is called out in `CHANGELOG.md` under a breaking-changes heading.

### S14 — [O] Single-source the `#[Param]` expander
`_expand_config_references` exists twice, in `commands/generate.py` and `commands/bootstrap.py`, and `CLAUDE.md` instructs contributors to keep the two copies in sync by hand. The circular-reference defect in S2 is present in both, which is what duplication of this kind reliably produces.

**Acceptance criteria**
- One implementation, imported by both commands.
- The `CLAUDE.md` note about keeping the copies in sync is removed.
- Existing tests for both commands still pass against the shared implementation.

### S15 — [O] Dead code cleanup
Two pieces of code that cannot affect behaviour: the two unreachable `if` branches in `_yaml_value` (folded into S4), and the `"CopyrightYear": date.today().year` entry in the `_generate_config_file` context at `commands/bootstrap.py:292`, which nothing reads — `cli-wizard.yaml.j2` sources that field from `_values`. The second is misleading rather than harmful: it looks like it overrides the prompted year, and does not.

**Acceptance criteria**
- The unused context entry is removed.
- The unreachable branches are gone (delivered by S4).
- Generated output is byte-identical before and after.

### S16 — [O] Initialize `CliGenerator` state in the constructor
`cli_name` and `package_name` are assigned in `generate()` rather than `__init__`, so `_template_context` raises `AttributeError` if any `_generate_*` method is called directly — as a test or a future caller reasonably might.

**Acceptance criteria**
- Both attributes are initialized in `__init__`.
- Calling a `_generate_*` method without `generate()` produces a clear error or works, not an `AttributeError` about a missing attribute.

### S17 — [O] Make the test suite resolve the package under test
With an editable install present, `pytest` run from a git worktree imports `cli_wizard` from whichever checkout the install points at, not the working tree. This was observed producing a spurious `TemplateNotFound` failure for `.github/workflows/changelog-enforcer.yaml` — the code under test was correct, but a different checkout supplied the templates. The failure mode is worse than a false alarm: the suite can pass while testing code that is not the code being changed.

**Acceptance criteria**
- `pytest` from a clean checkout or worktree tests that tree's sources, regardless of any editable install.
- The tox environments are unaffected.
- `DEVELOPMENT.md` documents how to run the suite against the working tree.
