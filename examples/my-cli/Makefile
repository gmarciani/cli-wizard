.PHONY: install test lint format build clean coverage

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v

coverage:
	pytest tests/ -v --cov=my_cli --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	autoflake --in-place --remove-all-unused-imports --recursive src/ tests/

build:
	python -m build

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
