# Makefile for instapaper-scraper

.PHONY: all install lint format type-check test test-cov check license-check build publish clean

# ====================================================================================
# HELP
# ====================================================================================

help: ## Show this help message.
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)


# ====================================================================================
# DEVELOPMENT
# ====================================================================================

all: check ## Run all checks.

install: ## Install dependencies for development.
	@echo "--> Installing development dependencies..."
	@pip install -e .[dev]

lint: ## Check code for linting errors with ruff.
	@echo "--> Linting code with ruff..."
	@ruff check .

format: ## Format code with ruff.
	@echo "--> Formatting code with ruff..."
	@ruff format .

type-check: ## Run static type checking with mypy.
	@echo "--> Running static type checking with mypy..."
	@mypy src

test: ## Run tests with pytest.
	@echo "--> Running tests with pytest..."
	@pytest

test-cov: ## Run tests with pytest and generate a coverage report.
	@echo "--> Running tests with coverage..."
	@pytest --cov=src/instapaper_scraper --cov-report=term-missing

check: lint type-check test ## Run all checks (lint, type-check, test).
	@echo "--> All checks passed."

license-check: ## Run license checks.
	@echo "--> Checking licenses..."
	@licensecheck --zero

# ====================================================================================
# BUILD & PUBLISH
# ====================================================================================

build: ## Build the project distribution packages.
	@echo "--> Building distribution packages..."
	@python -m build

publish: build ## Publish the packages to PyPI. Use with caution.
	@echo "--> Publishing to PyPI..."
	@echo "WARNING: This will upload packages to PyPI. Press Ctrl+C to cancel."
	@sleep 5
	@twine upload dist/*

# ====================================================================================
# CLEANUP
# ====================================================================================

clean: ## Remove temporary build and cache files.
	@echo "--> Cleaning up temporary files..."
	@rm -rf .ruff_cache .pytest_cache .mypy_cache build dist *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "--> Cleanup complete."
