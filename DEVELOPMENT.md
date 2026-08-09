# Development

## Setup

Setup development environment:

```shell
make setup
```

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

Interpreters you do not have installed are skipped with a `SKIPPED` line rather
than failing, so a missing version is easy to miss locally. CI installs one
version per job and runs exactly that environment, so nothing is skipped there.
To run the whole matrix locally, install the missing versions first — with
pyenv:

```shell
pyenv install 3.12 3.13 3.14
```

The supported range is declared once, in `SUPPORTED_PYTHON_VERSIONS` in
[src/cli_wizard/config/schema.py](src/cli_wizard/config/schema.py). It drives
cli-wizard's classifiers, tox envlist and CI matrix, and — through a generated
project's `PythonVersion` — the same four things in everything cli-wizard
generates. Tests fail if any of them disagree, so adding a version means
updating `tox.ini` and `.github/workflows/test.yaml` alongside the constant.

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
