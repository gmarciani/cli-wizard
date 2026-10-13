# Development

## Prerequisites

- Python 3.12 or newer.
- pip 25.1 or newer. The development toolchain is a
  [PEP 735](https://peps.python.org/pep-0735/) dependency group rather than an
  extra, and `pip install --group` landed in 25.1. `make install` upgrades pip
  before installing.

## Setup

Setup development environment:

```shell
make install
```

Every environment that needs the toolchain installs it the same way, whether it
is your machine or CI:

```shell
pip install -e . --group dev
```

my_cli publishes no extras at all. The toolchain lives in
[PEP 735](https://peps.python.org/pep-0735/) `[dependency-groups]`, which is
local-only metadata that never reaches an index:

| Group | Contents | Installed by |
|---|---|---|
| `test` | pytest, pytest-cov | the interpreter envs, and `dev` via `include-group` |
| `dev` | `test`, plus build, mypy, pre-commit, ruff, tox, twine, type stubs | `make install`, CI |

`dev` pulls `test` in through `{include-group = "test"}`,
so one command gets everything and there is no second recipe to keep in sync.
Versions are declared in those groups once; `tox.ini` reads them through
`dependency_groups` instead of repeating them.

Nothing here ships with the package: the built wheel and sdist contain `src/`
only, so a published test extra would install pytest for someone with no tests
to run it against.

## Validate
Run tests and linters:

```shell
# Run all tests and linting with tox
tox

# Run specific environments
tox -e test        # Unit tests
tox -e coverage    # Code coverage report
tox -e lint        # Linting only
tox -e type        # Type checking only
tox -e format      # Format code
```

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

Bump the version with the Bump Version workflow: run it with the target
version, and merge the pull request it opens. The workflow runs
`tools/bump_version.py`, which writes `VERSION` and opens the version's section
in `CHANGELOG.md`, warning about whichever is already there; a branch already
at that version gets no pull request. Run the script locally instead, if you
prefer:

```shell
python tools/bump_version.py 1.2.3
```

Once the bump is merged and the version's section in `CHANGELOG.md` is
written, draft the release with the Draft Release workflow: run it, with no
input, and it checks out `main` and runs `tools/draft_release.sh`. The script
reads the version from `VERSION`, takes the release notes from that section,
and creates the draft `v<VERSION>` release targeting `main` with
[gh](https://cli.github.com). A version that is already released, drafted, or
tagged on origin is refused with an error. Run the script locally instead, if
you prefer:

```shell
tools/draft_release.sh
```

Review the release notes on GitHub, and publish

```shell
gh release edit "v$(cat VERSION)" --draft=false
```

This will automatically publish to PyPI at https://pypi.org/project/my_cli.

### Manual Test PyPI Publishing

To manually publish to Test PyPI

```shell
python -m build
python -m twine upload --repository testpypi dist/*
```

### Demo
The product demo is a video that emulates the terminal behavior.
The video is generated with [Terminalizer](https://www.terminalizer.com/).
To generate the vide:
```
nvm use 20
npm install -g node-gyp terminalizer
terminalizer render resources/brand/demo.yml --output resources/brand/demo.mp4
```
