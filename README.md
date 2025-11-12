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
- `cryptography`

Install all dependencies using the provided requirements.txt:

```sh
pip install -r requirements.txt
```

## Setup
1. Clone or download the repository.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Run the script:
   ```sh
   python scrape.py
   ```

### Authentication
The script authenticates using one of the following methods, in order of priority:

1.  **Environment Variables**: Credentials are loaded from `INSTAPAPER_USERNAME` and `INSTAPAPER_PASSWORD` if they are set in your environment or in an `.env` file. This is the recommended method for automation.

    ```
    INSTAPAPER_USERNAME=your_username
    INSTAPAPER_PASSWORD=your_password
    ```

2.  **Session File**: If environment variables are not found, the script attempts to load a previously saved session from an encrypted `.instapaper_session` file.

3.  **Interactive Prompt**: If neither of the above methods is successful, the script will interactively prompt you for your username and password.

Upon a first-time successful login, the script generates a `.session_key` for encryption and saves your session to a `.instapaper_session` file to streamline future runs. Both files are created with secure permissions (read/write for owner only).

## Environment Variables
- `INSTAPAPER_USERNAME`: Your Instapaper account username
- `INSTAPAPER_PASSWORD`: Your Instapaper account password
- `ENABLE_FOLDER_MODE`: Set to 'true' to scrape a specific folder
- `FOLDER_ID_AND_SLUG`: The folder ID and slug when folder mode is enabled

## How It Works
The script is architected into modular, reusable "Transactions" that are executed by an Application runner.

1. **Authenticate and Verify**: The script authenticates with Instapaper by first checking for environment variables, then for a saved session file, and finally prompting for credentials if needed. The session is persisted for future use. The script verifies successful login and exits if authentication fails.
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

## Testing

This project includes a suite of unit tests to ensure functionality and prevent regressions.

To run the tests, execute the following command from the project root:

```sh
python -m unittest test_scrape.py
```

The test suite covers:
- Creation and permissions of the encryption key file.
- Correct encryption and decryption of the session file.

To improve testability, the main scraper function `run_instapaper_scraper` was refactored to accept optional file paths for the session and key files. This allows the tests to run in isolation without affecting user-generated session data.

## Future Enhancements

Below is a list of potential features and ideas for future development:

- [ ] **Enhanced Folder Configuration:**

  - [ ] Load `FOLDER_ID_AND_SLUG` from a command-line argument or a configuration file.
  - [ ] Add validation for the `FOLDER_ID_AND_SLUG` format.
  - [ ] Implement error handling for when folder mode is enabled without a valid folder identifier.
  - [ ] Introduce an interactive prompt for folder selection if multiple options exist.

- [ ] **Silent Output Mode:**
  - [ ] Add a `--silent` flag to suppress `stdout` logging, which is useful when directing output to a file.

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

## License

This project is licensed under the terms of the GNU General Public License v3.0. See the [LICENSE.md](LICENSE.md) file for the full license text.
