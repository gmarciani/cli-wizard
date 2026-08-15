# Development

## Prerequisites

- Python 3.12, 3.13 or 3.14 — see [Python versions](#python-versions).
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

tox does not install interpreters, it only discovers them, and it fails rather
than skipping when one is missing. Install the versions you do not have first —
with pyenv:

```shell
pyenv install 3.12 3.13 3.14
```

The supported range is declared once, in `SUPPORTED_PYTHON_VERSIONS` in
[src/cli_wizard/config/schema.py](src/cli_wizard/config/schema.py). It drives
cli-wizard's classifiers, tox envlist and CI matrix, and — through a generated
project's `PythonVersion` — the same in everything cli-wizard generates. Tests
fail if any of them disagree, so adding a version means updating `tox.ini` and
`.github/workflows/test.yaml` alongside the constant.

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

Update version in `VERSION`

Draft the release

```shell
VERSION="$(cat VERSION)"
gh release create v${VERSION} \
   --title v${VERSION} \
   --target main \
   --notes-file CHANGELOG.md \
   --latest \
   --draft
```

Make changes to the release notes, and publish

```shell
gh release edit v${VERSION} --draft=false
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
