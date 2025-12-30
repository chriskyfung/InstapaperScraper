# Instapaper Scraper

<!-- Badges -->
<p align="center">
  <a href="https://pypi.org/project/instapaper-scraper/">
    <img src="https://img.shields.io/pypi/v/instapaper-scraper.svg" alt="PyPI version">
  </a>
  <a href="https://pepy.tech/projects/instapaper-scraper">
    <img src="https://static.pepy.tech/personalized-badge/instapaper-scraper?period=total&left_text=downloads" alt="PyPI Downloads">
  </a>
  <a href="https://github.com/chriskyfung/InstapaperScraper">
    <img src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fchriskyfung%2FInstapaperScraper%2Frefs%2Fheads%2Fmaster%2Fpyproject.toml" alt="Python Version from PEP 621 TOML">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fruff%2Fmain%2Fassets%2Fbadge%2Fv2.json" alt="Ruff">
  </a>
  <a href="https://codecov.io/gh/chriskyfung/InstapaperScraper">
    <img src="https://codecov.io/gh/chriskyfung/InstapaperScraper/graph/badge.svg" alt="Code Coverage">
  </a>
  <wbr />
  <a href="https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml">
    <img src="https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://www.gnu.org/licenses/gpl-3.0.en.html">
    <img src="https://img.shields.io/github/license/chriskyfung/InstapaperScraper" alt="GitHub License">
  </a>
  <a href="https://github.com/sponsors/chriskyfung" title="Sponsor on GitHub">
    <img src="https://img.shields.io/badge/Sponsor-GitHub-blue?logo=github-sponsors&colorA=263238&colorB=EC407A" alt="GitHub Sponsors Default">
  </a>
  <a href="https://www.buymeacoffee.com/chriskyfung" title="Support Coffee">
    <img src="https://img.shields.io/badge/Support-Coffee-ffdd00?logo=buy-me-a-coffee&logoColor=ffdd00&colorA=263238" alt="Buy Me A Coffee">
  </a>
</p>

A powerful and reliable Python tool to automate the export of all your saved Instapaper bookmarks into various formats, giving you full ownership of your data.

## ✨ Features

- Scrapes all bookmarks from your Instapaper account.
- Supports scraping from specific folders.
- Exports data to CSV, JSON, or a SQLite database.
- Securely stores your session for future runs.
- Modern, modular, and tested architecture.

## 🚀 Getting Started

### 📋 1. Requirements

- Python 3.9+

### 📦 2. Installation

This package is available on PyPI and can be installed with pip:

```sh
pip install instapaper-scraper
```

### 💻 3. Usage

Run the tool from the command line, specifying your desired output format:

```sh
# Scrape and export to the default CSV format
instapaper-scraper

# Scrape and export to JSON
instapaper-scraper --format json

# Scrape and export to a SQLite database with a custom name
instapaper-scraper --format sqlite --output my_articles.db
```

## ⚙️ Configuration

### 🔐 Authentication

The script authenticates using one of the following methods, in order of priority:

1. **Command-line Arguments**: Provide your username and password directly when running the script:

    ```sh
    instapaper-scraper --username your_username --password your_password
    ```

2. **Session Files (`.session_key`, `.instapaper_session`)**: The script attempts to load these files in the following order:
    a.  Path specified by `--session-file` or `--key-file` arguments.
    b.  Files in the current working directory (e.g., `./.session_key`).
    c.  Files in the user's configuration directory (`~/.config/instapaper-scraper/`).
    After the first successful login, the script creates an encrypted `.instapaper_session` file and a `.session_key` file to reuse your session securely.

3. **Interactive Prompt**: If no other method is available, the script will prompt you for your username and password.

> **Note on Security:** Your session file (`.instapaper_session`) and the encryption key (`.session_key`) are stored with secure permissions (read/write for the owner only) to protect your credentials.

### 📁 Folder Configuration

You can define and quickly access your Instapaper folders using a `config.toml` file. The scraper will look for this file in the following locations (in order of precedence):

1. The path specified by the `--config-path` argument.
2. `config.toml` in the current working directory.
3. `~/.config/instapaper-scraper/config.toml`

Here is an example of `config.toml`:

```toml
# Default output filename for non-folder mode
output_filename = "home-articles.csv"

[[folders]]
key = "ml"
id = "1234567"
slug = "machine-learning"
output_filename = "ml-articles.json"

[[folders]]
key = "python"
id = "7654321"
slug = "python-programming"
output_filename = "python-articles.db"
```

- **output_filename (top-level)**: The default output filename to use when not in folder mode.
- **key**: A short alias for the folder.
- **id**: The folder ID from the Instapaper URL.
- **slug**: The human-readable part of the folder URL.
- **output_filename (folder-specific)**: A preset output filename for scraped articles from this specific folder.

When a `config.toml` file is present and no `--folder` argument is provided, the scraper will prompt you to select a folder. You can also specify a folder directly using the `--folder` argument with its key, ID, or slug. Use `--folder=none` to explicitly disable folder mode and scrape all articles.

### 💻 Command-line Arguments

| Argument | Description |
| --- | --- |
| `--config-path <path>`| Path to the configuration file. Searches `~/.config/instapaper-scraper/config.toml` and `config.toml` in the current directory by default. |
| `--folder <value>` | Specify a folder by key, ID, or slug from your `config.toml`. **Requires a configuration file to be loaded.** Use `none` to explicitly disable folder mode. If a configuration file is not found or fails to load, and this option is used (not set to `none`), the program will exit. |
| `--format <format>` | Output format (`csv`, `json`, `sqlite`). Default: `csv`. |
| `--output <filename>` | Specify a custom output filename. The file extension will be automatically corrected to match the selected format. |
| `--username <user>` | Your Instapaper account username. |
| `--password <pass>` | Your Instapaper account password. |
| `--add-instapaper-url` | Adds a `instapaper_url` column to the output, containing a full, clickable URL for each article. |

### 📄 Output Formats

You can control the output format using the `--format` argument. The supported formats are:

- `csv` (default): Exports data to `output/bookmarks.csv`.
- `json`: Exports data to `output/bookmarks.json`.
- `sqlite`: Exports data to an `articles` table in `output/bookmarks.db`.

If the `--format` flag is omitted, the script will default to `csv`.

When using `--output <filename>`, the file extension is automatically corrected to match the chosen format. For example, `instapaper-scraper --format json --output my_articles.txt` will create `my_articles.json`.

#### 📖 Opening Articles in Instapaper

The output data includes a unique `id` for each article. You can use this ID to construct a URL to the article's reader view: `https://www.instapaper.com/read/<article_id>`.

For convenience, you can use the `--add-instapaper-url` flag to have the script include a full, clickable URL in the output.

```sh
instapaper-scraper --add-instapaper-url
```

This adds a `instapaper_url` field to each article in the JSON output and a `instapaper_url` column in the CSV and SQLite outputs. The original `id` field is preserved.

## 🛠️ How It Works

The tool is designed with a modular architecture for reliability and maintainability.

1. **Authentication**: The `InstapaperAuthenticator` handles secure login and session management.
2. **Scraping**: The `InstapaperClient` iterates through all pages of your bookmarks, fetching the metadata for each article with robust error handling and retries. Shared constants, like the Instapaper base URL, are managed through `src/instapaper_scraper/constants.py`.
3. **Data Collection**: All fetched articles are aggregated into a single list.
4. **Export**: Finally, the collected data is written to a file in your chosen format (`.csv`, `.json`, or `.db`).

## 📊 Example Output

### 📄 CSV (`output/bookmarks.csv`) (with --add-instapaper-url)

```csv
"id","instapaper_url","title","url"
"999901234","https://www.instapaper.com/read/999901234","Article 1","https://www.example.com/page-1/"
"999002345","https://www.instapaper.com/read/999002345","Article 2","https://www.example.com/page-2/"
```

### 📄 JSON (`output/bookmarks.json`) (with --add-instapaper-url)

```json
[
    {
        "id": "999901234",
        "title": "Article 1",
        "url": "https://www.example.com/page-1/",
        "instapaper_url": "https://www.instapaper.com/read/999901234"
    },
    {
        "id": "999002345",
        "title": "Article 2",
        "url": "https://www.example.com/page-2/",
        "instapaper_url": "https://www.instapaper.com/read/999002345"
    }
]
```

### 🗄️ SQLite (`output/bookmarks.db`)

A SQLite database file is created with an `articles` table. The table includes `id`, `title`, and `url` columns. If the `--add-instapaper-url` flag is used, a `instapaper_url` column is also included. This feature is fully backward-compatible and will automatically adapt to the user's installed SQLite version, using an efficient generated column on modern versions (3.31.0+) and a fallback for older versions.

## 🤗 Support and Community

- **🐛 Bug Reports:** For any bugs or unexpected behavior, please [open an issue on GitHub](https://github.com/chriskyfung/InstapaperScraper/issues).
- **💬 Questions & General Discussion:** For questions, feature requests, or general discussion, please use our [GitHub Discussions](https://github.com/chriskyfung/InstapaperScraper/discussions).

## 🙏 Support the Project

`Instapaper Scraper` is a free and open-source project that requires significant time and effort to maintain and improve. If you find this tool useful, please consider supporting its development. Your contribution helps ensure the project stays healthy, active, and continuously updated.

- **[Sponsor on GitHub](https://github.com/sponsors/chriskyfung):** The best way to support the project with recurring monthly donations. Tiers with special rewards like priority support are available!
- **[Buy Me a Coffee](https://www.buymeacoffee.com/chriskyfung):** Perfect for a one-time thank you.

## 🤝 Contributing

Contributions are welcome! Whether it's a bug fix, a new feature, or documentation improvements, please feel free to open a pull request.

Please read the **[Contribution Guidelines](CONTRIBUTING.md)** before you start.

## 🧑‍💻 Development & Testing

This project uses `pytest` for testing, `ruff` for code formatting and linting, and `mypy` for static type checking.

### 🔧 Setup

To install the development dependencies:

```sh
pip install -e .[dev]
```

To set up the pre-commit hooks:

```sh
pre-commit install
```

### ▶️ Running the Scraper

To run the scraper directly without installing the package:

```sh
python -m src.instapaper_scraper.cli
```

### ✅ Testing

To run the tests, execute the following command from the project root:

```sh
pytest
```

To check test coverage:

```sh
pytest --cov=src/instapaper_scraper --cov-report=term-missing
```

### ✨ Code Quality

To format the code with `ruff`:

```sh
ruff format .
```

To check for linting errors with `ruff`:

```sh
ruff check .
```

To automatically fix linting errors:

```sh
ruff check . --fix
```

To run static type checking with `mypy`:

```sh
mypy src
```

To run license checks:

```sh
licensecheck --show-only-failing
```


## 📜 Disclaimer

This script requires valid Instapaper credentials. Use it responsibly and in accordance with Instapaper’s Terms of Service.

## 📄 License

This project is licensed under the terms of the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for the full license text.

## Contributors

[![Contributors](https://contrib.rocks/image?repo=chriskyfung/InstapaperScraper)](https://github.com/chriskyfung/InstapaperScraper/graphs/contributors)

Made with [contrib.rocks](https://contrib.rocks).
