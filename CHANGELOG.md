# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02-03

### Added
- A new `--article-preview` flag (and its older alias `--add-article-preview`) to include the article preview text in the output.
- Configuration file support for `add_instapaper_url` and `add_article_preview` options in the `[fields]` section of `config.toml`.

### Changed
- Renamed `--add-instapaper-url` to `--read-url` for brevity. The old flag is kept for backward compatibility.
- Both `--read-url` and `--article-preview` now support `--no-` prefixes (e.g., `--no-read-url`) to override `true` values from the config file.

## [1.1.1] - 2025-12-30

### Added
- A "Contributors" section in `README.md` to visually credit all project contributors.

### Changed
- **Developer Experience & Tooling**:
  - Added `ruff` linting and `mypy` static type checking to the CI pipeline to improve code quality.
  - Integrated automated license compliance checks using `licensecheck` into the CI pipeline.
  - Configured Dependabot to automatically update GitHub Actions on a weekly basis.
- **Performance**:
  - Improved application startup time by deferring the import of `json`, `sqlite3`, and `csv` modules to when they are specifically needed.
- **Dependencies**:
  - Updated the `actions/checkout` GitHub Action to v6 and `actions/setup-python` to v6.

## [1.1.0] - 2025-12-25

### Added
- A new `--add-instapaper-url` command-line argument to include a full, clickable URL for each article in the output.

### Changed
- **Developer Experience & Tooling**:
  - Migrated development tools from `black` to `ruff` for formatting and linting, and integrated `pre-commit` hooks to automate code quality checks.
  - Configured the `mypy` pre-commit hook to only run on the `src/` directory to improve performance.
- **Testing**:
  - Added comprehensive tests for API and authentication error handling to improve robustness.
  - Configured Codecov with new project and pull request coverage targets.
- **Output & Export**:
  - The output filename extension is now automatically corrected based on the selected format (e.g., providing `--output my-file.txt --format csv` will result in `my-file.csv`).
  - CSV output is now fully RFC 4180 compliant, with all fields quoted to improve compatibility with spreadsheet applications.
  - SQLite output is optimized to use a generated column for the `instapaper_url` on modern SQLite versions (>=3.31.0), with a fallback for older versions to ensure compatibility.
- **Robustness & Error Handling**:
  - Improved the CLI's resilience by adding robust error handling to gracefully manage exceptions during the file-saving process.
  - Enhanced the API client's robustness in handling malformed HTML and network errors, particularly for rate-limiting (HTTP 429) scenarios.
- **Internal Refactoring**:
  - Restructured internal constants management into a centralized and more organized architecture, improving code clarity and maintainability.
- **Documentation**:
    - Updated project badges in `README.md` for clarity and correctness.

### Fixed
- Improved type safety and robustness across the codebase.

## [1.0.0] - 2025-11-20

First official public release on PyPI.

### Added
- `pyproject.toml` for project configuration and dependency management.
- A `src` layout for the main application code.
- A `tests` directory for the test suite.
- A GitHub Actions workflow for CI/CD to automate linting, formatting, and testing.
- `pytest`, `pytest-cov`, and `requests-mock` for testing.
- `black` and `ruff` for code formatting and linting.
- Added support for JSON and SQLite output formats via the `--format` command-line argument.
- Added support for custom output filename via the `--output` command-line argument.

### Changed
- The project is now a standard Python package, installable with `pip`.
- The main script has been replaced by a command-line entry point (`instapaper-scraper`).
- Decomposed the original `scrape.py` into logical modules (`api`, `auth`, `cli`, `output`, `exceptions`).
- Migrated all tests from `unittest` to `pytest`, using fixtures and parametrization.
- Updated `README.md` to reflect the new project structure, installation, and usage.
- The default output format is now CSV, but users can choose between CSV, JSON, and SQLite.

### Removed
- `requirements.txt` in favor of `pyproject.toml`.
- The old `scrape.py` script.
- The old `unittest`-based test files.

### Deprecated
- The 'page' number has been removed from the output data. Users can now open a specific article on Instapaper by appending the article's unique ID to the base URL: `https://www.instapaper.com/read/<article_id>`.

## [0.4.0] - 2025-11-13

### Added
- Implemented session persistence with encryption to streamline authentication.
- Introduced `ScraperStructureChanged` custom exception for better error handling on HTML structure changes.
- Added comprehensive tests for error handling in `test_scrape_error_handling.py`.

### Fixed
- Implemented robust error handling with exponential backoff and retry logic for transient network errors (Fixes #27).
- Added handling for HTTP 429 (Too Many Requests) errors, respecting `Retry-After` headers.
- Improved HTML parsing to gracefully handle missing elements.

### Chore
- Updated dependencies: `cryptography` to 44.0.1 and `certifi` to 2025.11.12.
- Updated `README.md` to reflect the new authentication flow and dependencies.

## [0.3.0] - 2025-11-11

### Added
- Implemented basic logging and login verification for better debugging and security.

### Changed
- Renamed scrape-transactions.py to scrape.py as main project file.
- Improved HTTP error handling and logging in the scraper.
- Refactored article data handling to use dictionaries for better data structure.

### Chore
- Updated dependencies: `idna`, `requests`, `python-dotenv`, `soupsieve`.
- Updated documentation for the new modular architecture.
- Added a `LICENSE` file (GNU GPLv3).
- Adjusted the Dependabot configuration for grouped updates.

## [0.2.1] - 2023-03-07

### Changed
- Updated various dependencies to their latest versions.

## [0.2.0] - 2023-03-06

### Added
- Added Dependabot and funding configuration files.

### Fixed
- Addressed an issue with handling non-200 status codes during scraping.
- Corrected a boolean conversion error.

### Changed
- Implemented a new transactional pattern for scraping.
- Pinned `guara` dependency to a specific version.

## [0.1.0] - 2023-03-05

### Added
- Introduced support for scraping articles from specific Instapaper folders.

### Changed
- Removed unused functions and cleaned up imports for a more efficient codebase.

### Chore
- Added an example environment configuration file.
- Updated the `README.md` to reflect new features like CSV export and folder mode.
