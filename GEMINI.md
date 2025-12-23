# GEMINI.md

## Project Overview

This project is a Python-based command-line tool named "Instapaper Scraper" designed to scrape all saved bookmarks from a user's Instapaper account. It can export the scraped data into various formats, including CSV, JSON, and SQLite.

The tool is built with a modular architecture:
-   **`auth.py`**: Handles secure authentication and session management.
-   **`api.py`**: Contains the core scraping logic, using `requests` for HTTP calls and `BeautifulSoup` for HTML parsing. It includes robust error handling and retry mechanisms.
-   **`cli.py`**: Provides the command-line interface using `argparse`, orchestrating the authentication, scraping, and output processes. It includes options for selecting output format, specifying folders, and adding a clickable `instapaper_url` for each article.
-   **`output.py`**: Manages the saving of scraped articles to the specified file format. It automatically corrects the output filename extension to match the chosen format (e.g., `.csv`, `.json`, `.db`). The CSV output is RFC 4180 compliant, with all fields quoted. For SQLite output, it uses a generated column for `instapaper_url` on modern SQLite versions (>=3.31.0) and includes a fallback mechanism for older versions to ensure compatibility.

The project uses `pytest` for testing, `ruff` for linting, and `black` for code formatting.

## Building and Running

### Installation

To install the necessary dependencies for development:

```bash
pip install -e .[dev]
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

-   **Code Formatting**: The project uses `black` for consistent code formatting. To format the code, run:
    ```bash
    black .
    ```
-   **Linting**: The project uses `ruff` for linting. To check for linting errors, run:
    ```bash
    ruff check .
    ```
-   **Entry Point**: The main entry point for the CLI tool is the `main` function in `src/instapaper_scraper/cli.py`.
-   **Configuration**: The tool can be configured via a `config.toml` file for specifying folders and output filenames.
-   **Constants Management**: Constants are managed using a hybrid approach:
    -   Shared constants used across multiple modules are defined as module-level variables in `src/instapaper_scraper/constants.py`.
    -   Local constants specific to a class are defined as class attributes within that class (e.g., `InstapaperClient`, `InstapaperAuthenticator`).
    -   Local constants within procedural modules (`cli.py`, `output.py`) are defined as module-level variables in their respective files.
-   **Dependencies**: Project dependencies are managed in `pyproject.toml`.
