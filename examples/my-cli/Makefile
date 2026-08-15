.PHONY: install test lint format build clean coverage

install:
	python -m pip install --upgrade pip
	pip install -e . --group dev
	pre-commit install

test:
	pytest tests/ -v

coverage:
	pytest tests/ -v --cov=my_cli --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

build:
	python -m build

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
