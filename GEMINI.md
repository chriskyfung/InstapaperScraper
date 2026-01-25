# GEMINI.md

## Project Overview

This project is a Python-based command-line tool named "Instapaper Scraper" designed to scrape all saved bookmarks from a user's Instapaper account. It can export the scraped data into various formats, including CSV, JSON, and SQLite.

The tool is built with a modular architecture:
-   **`auth.py`**: Handles secure authentication and session management.
-   **`api.py`**: Contains the core scraping logic, using `requests` for HTTP calls and `BeautifulSoup` for HTML parsing. It includes robust error handling and retry mechanisms.
-   **`cli.py`**: Provides the command-line interface using `argparse`, orchestrating the authentication, scraping, and output processes. It includes options for selecting output format and specifying folders. It allows enabling `instapaper_url` and `article_preview` fields via command-line flags (e.g., `--read-url`, `--article-preview`) or from a `config.toml` file, with command-line arguments taking precedence. It maintains backward compatibility with older flags (`--add-instapaper-url`, `--add-article-preview`).
-   **`output.py`**: Manages the saving of scraped articles to the specified file format. It automatically corrects the output filename extension to match the chosen format (e.g., `.csv`, `.json`, `.db`). The CSV output is RFC 4180 compliant, with all fields quoted. For SQLite output, it uses a generated column for `instapaper_url` on modern SQLite versions (>=3.31.0) and includes a fallback mechanism for older versions to ensure compatibility. It also includes the `article_preview` field in the output when requested.

The project uses `pytest` for testing, `ruff` for linting and formatting, `mypy` for static type checking, and `pre-commit` for automated checks.

## Building and Running

### Installation

To install the necessary dependencies for development:

```bash
pip install -e .[dev]
```

To set up the pre-commit hooks:
```bash
pre-commit install
```

### Running the Scraper

To run the scraper directly from the source code:

```bash
python -m src.instapaper_scraper.cli [ARGUMENTS]
```

For example, to scrape and export to JSON:

```bash
python -m src.instapaper_scraper.cli --format json
```

### Running Tests

To run the test suite:

```bash
pytest
```

To run tests with code coverage:

```bash
pytest --cov=src/instapaper_scraper --cov-report=term-missing
```

## Development Conventions

-   **Code Formatting**: The project uses `ruff` for consistent code formatting. To format the code, run:
    ```bash
    ruff format .
    ```
-   **Linting**: The project uses `ruff` for linting. To check for linting errors, run:
    ```bash
    ruff check .
    ```
-   **Static Type Checking**: The project uses `mypy` for static type checking. To run the type checker, use:
    ```bash
    mypy src
    ```
-   **License Checking**: The project uses `licensecheck` to ensure license compliance. To run the license checker, use:
    ```bash
    licensecheck --zero
    ```
-   **Pre-Commit Hooks**: This project uses `pre-commit` to run checks before each commit. The hooks are defined in `.pre-commit-config.yaml` and include `ruff` and `mypy`.
-   **Entry Point**: The main entry point for the CLI tool is the `main` function in `src/instapaper_scraper/cli.py`.
-   **Configuration**: The tool can be configured via a `config.toml` file for specifying folders, output filenames, and default fields to include (e.g., `read_url`, `article_preview`).
-   **Constants Management**: Constants are managed using a hybrid approach:
    -   Shared constants used across multiple modules are defined as module-level variables in `src/instapaper_scraper/constants.py`.
    -   Local constants specific to a class are defined as class attributes within that class (e.g., `InstapaperClient`, `InstapaperAuthenticator`).
    -   Local constants within procedural modules (`cli.py`, `output.py`) are defined as module-level variables in their respective files.
-   **Dependencies**: Project dependencies are managed in `pyproject.toml`.
