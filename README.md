# Instapaper Scraper

This script allows users to **scrape** all saved Instapaper bookmarks and export them as **CSV data**. This version uses a modular, transaction-based architecture.

## Features
- Scrapes all bookmarks from your Instapaper home page.
- Support scraping bookmarks from specific Instapaper folders.
- Export bookmarks metadata in CSV format.

## Requirements
The following Python libraries are required:
- `requests`
- `beautifulsoup4`
- `python-dotenv`
- `guara`

Install all dependencies using the provided requirements.txt:

```sh
pip install -r requirements.txt
```

## Setup
1. Clone or download the repository.
2. Create an `.env` file in the project root with your credentials:
    ```
    INSTAPAPER_USERNAME=your_username
    INSTAPAPER_PASSWORD=your_password
    ```
3. Run the script:
    ```sh
    # Output to console
    python scrape.py

    # Save output to CSV file
    python scrape.py > bookmarks.csv
    ```

## Environment Variables
- `INSTAPAPER_USERNAME`: Your Instapaper account username
- `INSTAPAPER_PASSWORD`: Your Instapaper account password
- `ENABLE_FOLDER_MODE`: Set to 'true' to scrape a specific folder
- `FOLDER_ID_AND_SLUG`: The folder ID and slug when folder mode is enabled

## How It Works
The script is architected into modular, reusable "Transactions" that are executed by an Application runner.

1. **Authenticate and Verify**: A `requests.Session` is created and logs into Instapaper using your credentials. The script verifies successful login and exits if authentication fails.
2. **Initialize Application**: The session is passed to a `guara.transaction.Application` instance, which will manage the execution of scraping tasks.
3. **Execute Transactions**: The application iterates through all bookmark pages, logging its progress, and repeatedly executing two transactions:
    - `GetArticleIDs`: Fetches the article metadata from a single page, with robust error handling for network issues.
    - `PrintArticlesInfo`: Prints the fetched data to the console in CSV format.
4. **Output CSV**: Prints bookmark data in CSV format with headers.

## Example Output
The script outputs CSV data with the following structure:

```csv
page,id,title,url
Page 1,999901234,"Article 1",https://www.example.com/page-1/
Page 1,999002345,"Article 2",https://www.example.com/page-2/
```

## Acknowledgments
This script is **forked and modified** from:
- [Original Gist by jaflo](https://gist.github.com/jaflo/description.md)
- [Forked Gist by domingogallardo](https://gist.github.com/domingogallardo/b6e615fce5f552db6b36261c96bd8d47)

Major modifications include:
- Switched from HTML/PDF downloads to CSV export format
- Added environment variable support using python-dotenv
- Implemented folder-specific bookmark scraping
- Enhanced documentation and examples

## Disclaimer
This script requires **valid Instapaper credentials**. Be cautious when using personal account information and ensure compliance with Instapaper’s Terms of Service.
