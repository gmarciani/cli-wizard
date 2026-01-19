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
tox -e test        # Tests on Python 3.12
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

Update version in `constants.py`

```shell
VERSION="1.0.0"
```

Draft the release

```shell
gh release create v${VERSION} \
   --title "v$VERSION" \
   --target main \
   --notes-file CHANGELOG.md \
   --latest \
   --draft
```

Make changes to the release notes, and publish

```shell
gh release edit v${VERSION} --draft=false
```

This will automatically trigger Test PyPI publishing

### Manual Test PyPI Publishing

To manually publish to Test PyPI

```shell
python -m build
python -m twine upload --repository testpypi dist/*
```
