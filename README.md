# Instapaper Scraper

[![CI](https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml/badge.svg)](https://github.com/chriskyfung/InstapaperScraper/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/chriskyfung/InstapaperScraper/branch/main/graph/badge.svg)](https://codecov.io/gh/chriskyfung/InstapaperScraper)

A Python script to scrape all your saved Instapaper bookmarks and export them to various formats.

## Features
- Scrapes all bookmarks from your Instapaper account.
- Supports scraping from specific folders.
- Exports data to CSV, JSON, or a SQLite database.
- Securely stores your session for future runs.

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
Clone the repository and install the dependencies:
```sh
git clone https://github.com/chriskyfung/InstapaperScraper.git
cd InstapaperScraper
pip install -r requirements.txt
```

### 3. Usage
Run the script from the command line, specifying your desired output format:
```sh
# Scrape and export to the default CSV format
python scrape.py

# Scrape and export to JSON
python scrape.py --format json

# Scrape and export to a SQLite database with a custom name
python scrape.py --format sqlite --output my_articles.db
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

## How It Works
The script uses a modular, transaction-based architecture to ensure reliability.
1. **Authentication**: The script securely logs into your Instapaper account.
2. **Scraping**: It then iterates through all pages of your bookmarks, fetching the metadata for each article.
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

## Testing

This project includes a suite of unit tests to ensure functionality and prevent regressions. To run the tests, execute the following command from the project root:
```sh
python -m unittest test_scrape.py
```

## Future Enhancements

- [ ] **Enhanced Folder Configuration**: Allow loading folder settings from a command-line argument.
- [ ] **Silent Output Mode**: Add a `--silent` flag to suppress non-essential logging.

## Disclaimer

This script requires valid Instapaper credentials. Use it responsibly and in accordance with Instapaper’s Terms of Service.

## License

This project is licensed under the terms of the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for the full license text.
