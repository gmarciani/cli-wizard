# Development

## Prerequisites

- Python 3.12, 3.13 or 3.14 — see [Python versions](#python-versions).
  The default is 3.14: `make setup` pins the release named in the `Makefile`,
  and tox, mypy and the single-version CI jobs run on it.
- [pyenv](https://github.com/pyenv/pyenv), used by `make setup` to create the
  virtualenv.
- pip 25.1 or newer. The development toolchain is a
  [PEP 735](https://peps.python.org/pep-0735/) dependency group rather than an
  extra, and `pip install --group` landed in 25.1. `make setup` upgrades pip
  before installing.

## Setup

Setup development environment:

```shell
make setup
```

Every environment that needs the toolchain installs it the same way, whether it
is your machine or CI:

```shell
pip install -e . --group dev
```

cli-wizard publishes no extras at all. The toolchain lives in
[PEP 735](https://peps.python.org/pep-0735/) `[dependency-groups]`, which is
local-only metadata that never reaches PyPI:

| Group | Contents | Installed by |
|---|---|---|
| `test` | `docs`, plus pytest, pytest-cov, mypy, type stubs | `tox -e py3xx`, and `dev` via `include-group` |
| `dev` | `test`, plus build, pre-commit, tox, twine | `make setup`, CI |
| `docs` | sphinx and its plugins | `make install-docs` |

`dev` pulls `test` in through `{include-group = "test"}`, so one command gets
everything and there is no second recipe to keep in sync. Versions are declared
in those groups once; `tox.ini` reads them through `dependency_groups` instead
of repeating them.

## Validate
Run tests and linters:

```shell
# Run all tests and linting with tox
tox

# Run specific environments
tox -e test        # Unit tests on the active interpreter
tox -e coverage    # Code coverage report
tox -e lint        # Linting only
tox -e type        # Type checking only
tox -e format      # Format code
```

A coverage run fails when total coverage drops below 90% (`fail_under` in
`pyproject.toml`). That applies to `tox -e test`, `tox -e coverage` and CI.

### Python versions

cli-wizard supports Python 3.12, 3.13 and 3.14, and generates projects that
support the same range. `tox` runs the suite on each of them:

```shell
tox -e py312       # Run the suite on a single version
tox -e py312,py313,py314
```

Every other tox environment (`test`, `lint`, `type`, `format`, `coverage`) runs
on the default interpreter, 3.14, declared as its `base_python` in `tox.ini`. The same
`DEFAULT_PYTHON_VERSION` is what a generated project targets when its config
leaves `PythonVersion` unset. Ruff
targets the oldest supported version so it never emits syntax 3.12 rejects;
mypy checks against the default.

tox does not install interpreters, it only discovers them, and it fails rather
than skipping when one is missing. Install the versions you do not have first —
with pyenv:

```shell
pyenv install 3.12 3.13 3.14
```

pyenv only exposes the interpreter selected by `.python-version`, so put the
others on `PATH` before running the matrix:

```shell
export PATH="$HOME/.pyenv/versions/3.12.13/bin:$HOME/.pyenv/versions/3.13.13/bin:$PATH"
```

The supported range is declared once, in `SUPPORTED_PYTHON_VERSIONS` in
[src/cli_wizard/config/schema.py](src/cli_wizard/config/schema.py). It drives
cli-wizard's classifiers, tox envlist, CI matrices and README badge, and —
through a generated project's `PythonVersion` — the same in everything
cli-wizard generates. Tests fail if any of them disagree, so adding a version
means updating `tox.ini`, `.github/workflows/test.yaml` and the README badge
alongside the constant. The `Required checks` ruleset on `main` names each
`test (<version>)` job, so update it in the repository settings as well.

## Documentation

Generate the CLI reference documentation using Sphinx:

```shell
make build-docs
```

The generated documentation will be in `docs/_build/html/`.

View the documentation:

```shell
make open-docs
```

Clean the documentation:

```shell
make clean-docs
```

## Continuous AI

These workflows run [Claude Code](https://code.claude.com/docs/en/github-actions)
on the repository through
[anthropics/claude-code-action](https://github.com/anthropics/claude-code-action).

| Workflow | Runs when | Does |
|---|---|---|
| [Code Review](.github/workflows/code-review.yaml) | a pull request is opened, pushed to, reopened or marked ready, or run by hand with a pull request's link | reviews the change and posts inline comments, or one comment when run by hand; read-only |
| [Product Manager: New Ideas](.github/workflows/product-manager-new-ideas.yaml) | Fridays at 9am ET, or run by hand | proposes five features and five bug fixes, each bug reproduced first, and opens an issue for each, labelled with its type, `Triage` and a priority |
| [Product Manager: Grooming](.github/workflows/product-manager-grooming.yaml) | Saturdays at 9am ET, or run by hand, for every open issue or the one whose link it is given | judges the labels and the priority of the open issues and changes those that differ; never `Triage` or `Planned` |
| [Engineer](.github/workflows/engineer.yaml) | Tuesdays at 9am ET, or run by hand | implements up to three open issues labelled `Planned`, oldest first, and opens a draft pull request for each |

They need, once:

1. The [Claude GitHub App](https://github.com/apps/claude) installed on the
   repository, so comments and pull requests are posted as Claude.
2. The `CLAUDE_CODE_OAUTH_TOKEN` repository secret, a token from your Claude
   subscription. Create it with Claude Code, signing in to your Claude
   account in the browser it opens, then store the token it prints:

   ```shell
   claude setup-token
   gh secret set CLAUDE_CODE_OAUTH_TOKEN
   ```

GitHub withholds secrets from pull requests opened from forks, so Code
Review skips them: run it by hand with the pull request's link to review one.

The Product Manager workflows and Engineer make a weekly loop: New Ideas
opens its proposals on Friday, Grooming puts the labels and priorities of the
open issues right on Saturday, you triage them and label `Planned` the ones
to build, and Engineer opens a draft pull request for each on Tuesday, once
the change passes `tox -e lint,type,test`. The label approves the issue's
text as it stands, so an issue edited afterwards waits to be labelled again.
An issue Engineer cannot implement gets a comment saying why and loses the
label.

Run Engineer by hand with either `issue`, the link of one issue to implement
even if it already had a pull request, or `max-issues`; not both.

The logic of both workflows' steps lives in scripts that run by hand too;
`--help` lists their commands and options:

```shell
# Print the issues a file of proposals would open, without opening them
tools/product_manager.py open proposals.json --dry-run

# Print the label changes a grooming file would make, without making them
tools/product_manager.py groom grooming.json --dry-run

# Check a pull request link the way a Code Review run by hand does
tools/code_review.py resolve --pull-request https://github.com/gmarciani/cli-wizard/pull/153

# List the issues Engineer would implement
tools/engineer.py select --max-issues 5
tools/engineer.py select --issue https://github.com/gmarciani/cli-wizard/issues/42

# From the branch engineer/issue-42, with the change committed: run the checks,
# then push it and open the draft pull request described in claude-pr.md
tools/engineer.py submit --number 42
```

## Release

Bump the version with the [Bump Version](https://github.com/gmarciani/cli-wizard/actions/workflows/bump-version.yaml)
workflow: run it with the target version, and merge the pull request it opens.
The workflow runs `tools/bump_version.py`, which writes `VERSION` and opens
the version's section in `CHANGELOG.md`, warning about whichever is already
there; a branch already at that version gets no pull request. Run the script
locally instead, if you prefer:

```shell
python tools/bump_version.py 3.1.0
```

Once the bump is merged and the version's section in `CHANGELOG.md` is
written, draft the release with the [Draft Release](https://github.com/gmarciani/cli-wizard/actions/workflows/draft-release.yaml)
workflow: run it, with no input, and it checks out `main` and runs
`tools/draft_release.sh`. The script reads the version from `VERSION`, takes
the release notes from that section, and creates the draft `v<VERSION>` release
targeting `main` with [gh](https://cli.github.com). A version that is already
released, drafted, or tagged on origin is refused with an error. Run the script
locally instead, if you prefer:

```shell
tools/draft_release.sh
```

Review the release notes on GitHub, and publish

```shell
gh release edit "v$(cat VERSION)" --draft=false
```

This will automatically publish to PyPI at https://pypi.org/project/cli-wizard.

### Demo
The product demo is a video that emulates the terminal behavior.
The video is generated with [Terminalizer](https://www.terminalizer.com/).
To generate the vide:
```
nvm use 20
npm install -g node-gyp terminalizer
terminalizer render resources/brand/demo.yml --output resources/brand/demo.mp4
```
