# Makefile for instapaper-scraper

.PHONY: all install lint format type-check test test-cov check license-check build publish clean

# ====================================================================================
# HELP
# ====================================================================================

help:
	@echo "Commands:"
	@echo "  install        : Install dependencies for development."
	@echo "  lint           : Check code for linting errors with ruff."
	@echo "  format         : Format code with ruff."
	@echo "  type-check     : Run static type checking with mypy."
	@echo "  test           : Run tests with pytest."
	@echo "  test-cov       : Run tests with pytest and generate a coverage report."
	@echo "  check          : Run all checks (lint, type-check, test)."
	@echo "  license-check  : Run license checks."
	@echo "  build          : Build the project distribution packages."
	@echo "  publish        : Publish the packages to PyPI. Use with caution."
	@echo "  clean          : Remove temporary build and cache files."
	@echo "  all            : Run all checks."


# ====================================================================================
# DEVELOPMENT
# ====================================================================================

all: check

install:
	@echo "--> Installing development dependencies..."
	@pip install -e .[dev]

lint:
	@echo "--> Linting code with ruff..."
	@ruff check .

format:
	@echo "--> Formatting code with ruff..."
	@ruff format .

type-check:
	@echo "--> Running static type checking with mypy..."
	@mypy src

test:
	@echo "--> Running tests with pytest..."
	@pytest

test-cov:
	@echo "--> Running tests with coverage..."
	@pytest --cov=src/instapaper_scraper --cov-report=term-missing

check: lint type-check test
	@echo "--> All checks passed."

license-check:
	@echo "--> Checking licenses..."
	@licensecheck --zero

# ====================================================================================
# BUILD & PUBLISH
# ====================================================================================

build:
	@echo "--> Building distribution packages..."
	@python -m build

publish: build
	@echo "--> Publishing to PyPI..."
	@echo "WARNING: This will upload packages to PyPI. Press Ctrl+C to cancel."
	@sleep 5
	@twine upload dist/*

# ====================================================================================
# CLEANUP
# ====================================================================================

clean:
	@echo "--> Cleaning up temporary files..."
	@rm -rf .ruff_cache .pytest_cache .mypy_cache build dist src/instapaper_scraper.egg-info __pycache__ src/instapaper_scraper/__pycache__ tests/__pycache__
	@echo "--> Cleanup complete."
