# GEMINI.md

## Project Overview

This project is a Python-based command-line tool named "Instapaper Scraper" designed to scrape all saved bookmarks from a user's Instapaper account. It can export the scraped data into various formats, including CSV, JSON, and SQLite.

The tool is built with a modular architecture:
-   **`auth.py`**: Handles secure authentication and session management.
-   **`api.py`**: Contains the core scraping logic, using `requests` for HTTP calls to the Instapaper JSON API (`/data/bookmarks` and `/data/user_session` endpoints). It includes robust error handling and retry mechanisms, automatic form key fetching and caching for API authentication, and parses JSON bookmark responses into structured article data with rich metadata (author, time, site_name, liked, is_archived, tags, notes). The migration from HTML scraping to the JSON API was required following Instapaper's complete website relaunch on July 28, 2026 ([announcement](https://blog.instapaper.com/2026/07/28/instapaper-10/)), which replaced the previous HTML-based interface with a modern single-page application.
-   **`cli.py`**: Provides the command-line interface using `argparse`, orchestrating the authentication, scraping, and output processes. It includes options for selecting output format and specifying folders, including the special "Liked" and "Archive" collections. It allows enabling `instapaper_url` and `article_preview` fields via command-line flags (e.g., `--read-url`, `--article-preview`) or from a `config.toml` file, with command-line arguments taking precedence. It maintains backward compatibility with older flags (`--add-instapaper-url`, `--add-article-preview`).
-   **`output.py`**: Manages the saving of scraped articles to the specified file format. It automatically corrects the output filename extension to match the chosen format (e.g., `.csv`, `.json`, `.db`). The CSV output is RFC 4180 compliant, with all fields quoted, and safely filters each row to only include keys defined in the fieldnames list to prevent errors when optional fields are not included. For SQLite output, it uses a generated column for `instapaper_url` on modern SQLite versions (>=3.31.0) and includes a fallback mechanism for older versions to ensure compatibility. It also includes the `article_preview` field in the output when requested.
-   **`exceptions.py`**: Defines custom exceptions including `InstapaperAPIError` for JSON API error responses and `ScraperStructureChanged` (which inherits from `InstapaperAPIError` for backward compatibility).
-   **`constants.py`**: Manages shared constants including JSON API URLs (`INSTAPAPER_BOOKMARKS_URL`, `INSTAPAPER_USER_SESSION_URL`), section types (`SECTION_HOME`, `SECTION_LIKED`, `SECTION_ARCHIVE`, `SECTION_FOLDER`), sort options (`SORT_NEWEST`, `SORT_OLDEST`), and article field keys for both core and rich metadata fields.

The project uses `pytest` for testing, `ruff` for linting and formatting, `mypy` for static type checking, and `pre-commit` for automated checks.

## Building and Running

### Installation

To install the necessary dependencies for development, you can use `pip` or the provided `Makefile`:

```bash
# Using pip
pip install -e .[dev]

# Or using make
make install
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

To run the test suite (or use `make test`):

```bash
pytest
```

To run tests with code coverage (or use `make test-cov`):

```bash
pytest --cov=src/instapaper_scraper --cov-report=term-missing
```

## Development Conventions

A `Makefile` is provided to simplify common development tasks. Run `make help` to see all available commands.

-   **Code Formatting**: The project uses `ruff` for consistent code formatting. To format the code, run:
    ```bash
    # Direct command
    ruff format .

    # Using Makefile
    make format
    ```
-   **Linting**: The project uses `ruff` for linting. To check for linting errors, run:
    ```bash
    # Direct command
    ruff check .

    # Using Makefile
    make lint
    ```
-   **Static Type Checking**: The project uses `mypy` for static type checking. To run the type checker, use:
    ```bash
    # Direct command
    mypy src

    # Using Makefile
    make type-check
    ```
-   **License Checking**: The project uses `licensecheck` to ensure license compliance. To run the license checker, use:
    ```bash
    # Direct command
    licensecheck --zero

    # Using Makefile
    make license-check
    ```
-   **Pre-Commit Hooks**: This project uses `pre-commit` to run checks before each commit. The hooks are defined in `.pre-commit-config.yaml` and include `ruff` and `mypy`.
-   **Entry Point**: The main entry point for the CLI tool is the `main` function in `src/instapaper_scraper/cli.py`.
-   **Configuration**: The tool can be configured via a `config.toml` file for specifying folders (including special collections like Liked and Archive), output filenames, and default fields to include (e.g., `read_url`, `article_preview`).
-   **Constants Management**: Constants are managed using a hybrid approach:
    -   Shared constants used across multiple modules are defined as module-level variables in `src/instapaper_scraper/constants.py`.
    -   Local constants specific to a class are defined as class attributes within that class (e.g., `InstapaperClient`, `InstapaperAuthenticator`).
    -   Local constants within procedural modules (`cli.py`, `output.py`) are defined as module-level variables in their respective files.
-   **Dependencies**: Project dependencies are managed in `pyproject.toml`.
