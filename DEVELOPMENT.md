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
| `test` | pytest, pytest-cov | `tox -e py3xx`, and `dev` via `include-group` |
| `dev` | `test`, plus build, mypy, pre-commit, tox, twine, type stubs | `make setup`, CI |
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
means updating `tox.ini`, `.github/workflows/test.yaml`,
`.github/workflows/pr-validation.yaml` and the README badge alongside the
constant.

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
