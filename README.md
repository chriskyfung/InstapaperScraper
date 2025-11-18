# Instapaper Scraper

[![CI](https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml/badge.svg)](https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/chriskyfung/InstapaperScraper/branch/main/graph/badge.svg?token=1OK83DVUA5)](https://codecov.io/gh/chriskyfung/InstapaperScraper)

A Python tool to scrape all your saved Instapaper bookmarks and export them to various formats.

## Features

- Scrapes all bookmarks from your Instapaper account.
- Supports scraping from specific folders.
- Exports data to CSV, JSON, or a SQLite database.
- Securely stores your session for future runs.
- Modern, modular, and tested architecture.

## Getting Started

### 1. Requirements
- Python 3.9+
- The following Python libraries:
  - `requests`
  - `beautifulsoup4`
  - `python-dotenv`
  - `guara`
  - `cryptography`

### 2. Installation

Clone the repository and install the package in editable mode. It is recommended to use a virtual environment.

```sh
git clone https://github.com/chriskyfung/InstapaperScraper.git
cd InstapaperScraper
python -m venv venv
source venv/bin/activate
pip install -e .
```

This will install the `instapaper-scraper` command-line tool and all its dependencies.

### 3. Usage

Run the tool from the command line, specifying your desired output format:

```sh
# Scrape and export to the default CSV format
instapaper-scraper

# Scrape and export to JSON
instapaper-scraper --format json

# Scrape and export to a SQLite database with a custom name
instapaper-scraper --format sqlite --output my_articles.db
```

## Configuration

### Authentication

The script authenticates using one of the following methods, in order of priority:

1.  **Environment Variables**: The recommended method for automation. Create a `.env` file in the project root or set the variables in your shell:

    ```
    INSTAPAPER_USERNAME=your_username
    INSTAPAPER_PASSWORD=your_password
    ```

2.  **Session File**: After the first successful login, the script creates an encrypted `.instapaper_session` file to reuse your session securely.

3.  **Interactive Prompt**: If no other method is available, the script will prompt you for your username and password.

> **Note on Security:** Your session file and the encryption key (`.session_key`) are created with secure permissions (read/write for the owner only) to protect your credentials.

### Output Formats

You can control the output format using the `--format` argument. The supported formats are:

- `csv` (default): Exports data to `output/bookmarks.csv`.
- `json`: Exports data to `output/bookmarks.json`.
- `sqlite`: Exports data to an `articles` table in `output/bookmarks.db`.
- `--output <filename>`: Specify a custom output filename.

If the `--format` flag is omitted, the script will default to `csv`.

#### Opening Articles in Instapaper

The output data includes a unique `id` for each article. To open an article directly in Instapaper's reader view, append this ID to the base URL:
`https://www.instapaper.com/read/<article_id>`

### Environment Variables

You can configure the script's behavior using the following environment variables:

| Variable              | Description                                                              |
| --------------------- | ------------------------------------------------------------------------ |
| `INSTAPAPER_USERNAME` | Your Instapaper account username.                                        |
| `INSTAPAPER_PASSWORD` | Your Instapaper account password.                                        |
| `ENABLE_FOLDER_MODE`  | Set to `true` to scrape a specific folder instead of the main archive.   |
| `FOLDER_ID_AND_SLUG`  | The ID and slug of the folder to scrape (e.g., `12345/my-folder-name`).  |
| `MAX_RETRIES`         | The maximum number of retries for a failed request (default: 3).         |
| `BACKOFF_FACTOR`      | The backoff factor for retries (default: 1).                             |


## How It Works

The tool is designed with a modular architecture for reliability and maintainability.

1. **Authentication**: The `InstapaperAuthenticator` handles secure login and session management.
2. **Scraping**: The `InstapaperClient` iterates through all pages of your bookmarks, fetching the metadata for each article with robust error handling and retries.
3. **Data Collection**: All fetched articles are aggregated into a single list.
4. **Export**: Finally, the collected data is written to a file in your chosen format (`.csv`, `.json`, or `.db`).

## Example Output

### CSV (`output/bookmarks.csv`)

```csv
id,title,url
999901234,"Article 1",https://www.example.com/page-1/
999002345,"Article 2",https://www.example.com/page-2/
```

### JSON (`output/bookmarks.json`)

```json
[
    {
        "id": "999901234",
        "title": "Article 1",
        "url": "https://www.example.com/page-1/"
    },
    {
        "id": "999002345",
        "title": "Article 2",
        "url": "https://www.example.com/page-2/"
    }
]
```

### SQLite (`output/bookmarks.db`)

A SQLite database file is created with an `articles` table containing `id`, `title`, and `url` columns.

## Development & Testing

This project uses `pytest` for testing, `black` for code formatting, and `ruff` for linting.

### Setup

To install the development dependencies:
```sh
pip install -e .[dev]
```

### Running the Scraper

To run the scraper directly without installing the package:

```sh
python -m src.instapaper_scraper.cli
```

### Testing

To run the tests, execute the following command from the project root:

```sh

pytest

```

To check test coverage:

```sh

pytest --cov=src/instapaper_scraper --cov-report=term-missing

```

### Code Quality

To format the code with `black`:

```sh
black .
```

To check for linting errors with `ruff`:

```sh
ruff check .
```

To automatically fix linting errors:

```sh
ruff check . --fix
```

### Continuous Integration
A GitHub Actions workflow is configured to run all checks (linting, formatting, and testing) automatically on every push and pull request.

## Disclaimer

This script requires valid Instapaper credentials. Use it responsibly and in accordance with Instapaper’s Terms of Service.

## License

This project is licensed under the terms of the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for the full license text.
