# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-19

### Added
- A new `--add-instapaper-url` command-line argument to include a full, clickable URL for each article in the output.

### Changed
- **Output & Export**:
  - The output filename extension is now automatically corrected based on the selected format (e.g., providing `--output my-file.txt --format csv` will result in `my-file.csv`).
  - CSV output is now fully RFC 4180 compliant, with all fields quoted to improve compatibility with spreadsheet applications.
  - SQLite output is optimized to use a generated column for the `instapaper_url` on modern SQLite versions (>=3.31.0), with a fallback for older versions to ensure compatibility.
- **Robustness & Error Handling**:
  - Improved the CLI's resilience by adding robust error handling to gracefully manage exceptions during the file-saving process.
  - Enhanced the API client's robustness in handling malformed HTML and network errors, particularly for rate-limiting (HTTP 429) scenarios.
- **Internal Refactoring**:
  - Restructured internal constants management into a centralized and more organized architecture, improving code clarity and maintainability.

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


