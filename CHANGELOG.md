# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Session Reuse**: Fixed stored sessions never being reused (the tool re-logged-in on every run). Root cause: the `/u` endpoint now returns 200 regardless of login state, so session verification always failed. Verification now probes `/data/user_session`, which returns a JSON payload with a `user` object only for authenticated sessions.

### Changed
- **Session File Format v2**: The encrypted session file now stores all cookies (not just the auth cookies) as a JSON payload with `domain`, `path`, and `secure` attributes. The JSON format is immune to special characters in cookie values. Legacy v1 session files are still loaded and are upgraded automatically on the next save.
- **Form Key Hand-off**: The `x-form-key` is now captured during session verification and passed directly to the API client, avoiding a redundant request on the first scrape.

### Added
- **Two-stage Verification Fallback**: If verification with the full cookie jar is rejected, a retry is made with an explicit `Cookie` header containing only the auth cookies (`pfus`/`pfps`/`pfhs`), replicating the browser request exactly.
- **`--dump-session` CLI Flag**: Prints a masked summary of the stored session cookies for troubleshooting.
- **Post-save Self-check**: Every saved session file is fsynced, then re-read from disk, decrypted, and compared with what was written to detect partial writes or storage corruption at save time.
- **Configurable User-Agent**: The `User-Agent` sent to the API can be set via the `INSTAPAPER_USER_AGENT` environment variable or the `InstapaperClient(user_agent=...)` argument (defaults to a browser-like UA).
- **Documentation**: Added `docs/session-management.md` describing session storage, verification, and troubleshooting.

## [1.4.0] - 2026-08-09

### Added
- **API Rewrite**: Replaced HTML scraping with the Instapaper JSON API (`/data/bookmarks` and `/data/user_session` endpoints) for more reliable and efficient data retrieval. This was required following Instapaper's complete website relaunch on July 28, 2026, which replaced the previous HTML-based interface with a modern single-page application. See the [announcement blog post](https://blog.instapaper.com/2026/07/28/instapaper-10/) for details.
- **Rich Metadata**: Article data now includes additional fields from the JSON API: `author`, `time`, `site_name`, `liked`, `is_archived`, `tags`, and `notes`.
- **Form Key Management**: Added automatic fetching and caching of the `x-form-key` header from the user session endpoint for API authentication.
- **New Exception**: Added `InstapaperAPIError` exception class for JSON API error responses. `ScraperStructureChanged` now inherits from `InstapaperAPIError` for backward compatibility.
- **New Constants**: Added constants for JSON API URLs (`INSTAPAPER_BOOKMARKS_URL`, `INSTAPAPER_USER_SESSION_URL`), section types (`SECTION_HOME`, `SECTION_LIKED`, `SECTION_ARCHIVE`, `SECTION_FOLDER`), sort options (`SORT_NEWEST`, `SORT_OLDEST`), and additional article field keys (`KEY_AUTHOR`, `KEY_DESCRIPTION`, `KEY_TIME`, `KEY_SITE_NAME`, `KEY_TAGS`, `KEY_NOTES`, `KEY_LIKED`, `KEY_IS_ARCHIVED`).

### Changed
- **CLI**:
  - Moved authentication logic to the start of `main` to ensure login happens before folder selection and any processing.
  - Added error logging for failed login attempts.
- **API Client**:
  - Rewrote `InstapaperClient` to use the Instapaper JSON API instead of HTML parsing with BeautifulSoup.
  - Replaced `_get_page_url()` with `_build_request_params()` for constructing API query parameters.
  - Replaced `_parse_article_data()` with `_parse_bookmarks()` for parsing JSON bookmark objects.
  - Updated `get_articles()` to send requests to the bookmarks API endpoint with proper headers and query parameters.
  - Updated `get_all_articles()` to work with the new API response format.
- **Error Handling**:
  - Standardized exception hierarchy to use `InstapaperAPIError` as the base exception for all API-related errors.
  - Added specific exception classes `ApiParseError` and `ApiNetworkError` for more granular error handling.
  - Externalized session fetch error messages for better maintainability.
  - Added logging for session fetch errors to improve debuggability.
- **Code Quality**:
  - Configured `ruff` as the primary linter with appropriate rule sets.
  - Reorganized import statements following standard conventions.
  - Removed unused legacy URL constants from the codebase.
- **Exception Naming**:
  - Renamed `ScraperStructureChanged` to `ApiResponseError` to accurately reflect that this exception is raised for unexpected JSON API responses, not HTML DOM structure changes.
- **Dependencies**:
  - Bumped `cryptography` to v50.0.0 to fix CVE-2026-69247.
  - Bumped pre-commit hook versions.
  - Removed `beautifulsoup4` and `soupsieve` from core dependencies (no longer needed after API migration).
  - Removed `types-beautifulsoup4` from development dependencies and pre-commit hook configuration.
- **Testing**:
  - Migrated all API tests from HTML-based mocking to JSON-based mocking.
  - Replaced `get_mock_html()` with `get_mock_bookmarks_json()` for generating mock API responses.
  - Added `setup_session_mock()` helper for mocking the user session endpoint.
  - Updated folder tests to test `_build_request_params()` instead of the removed `_get_page_url()`.
  - Added tests for form key caching and rich metadata inclusion.
  - Removed tests for removed HTML parsing methods (`_parse_article_data`).

### Fixed
- **Auth**: Login against the post-relaunch Instapaper site (issue #105):
  - Preflight `GET /user/login` to acquire the `_xsrf` cookie and echo it in the
    POST body (server now returns `403` otherwise).
  - Recognise the new session cookie names (`pfus`, `pfps`, `pfhs`).
  - Recognise the new post-login redirect path (`/home` instead of `/u`).
- **CSV Output**: Fixed a `ValueError` in `save_to_csv` that occurred when data dictionaries contained extra keys not present in the fieldnames list. The writer now filters each row to only include keys defined in the fieldnames, preventing crashes when optional fields (e.g., `instapaper_url`, `article_preview`) are not included in the output.
- **Bookmark Parsing**: Skip bookmarks that are missing identification IDs instead of crashing, improving resilience when processing incomplete data.

## [1.3.3] - 2026-06-26

### Changed
- **Dependencies**:
  - Widened version requirements for core dependencies (`beautifulsoup4`, `certifi`, `cryptography`) and development tools (`pytest`, `mypy`) to allow newer compatible versions.

## [1.3.2] - 2026-06-01

### Changed
- **Dependencies**:
  - Widened version requirements for core dependencies (`certifi`, `cryptography`, `requests`, `urllib3`) and development tools (`build`, `mypy`) to allow newer compatible versions.

## [1.3.1] - 2026-04-28

### Added
- Added `context7.json` configuration file to enable Context7 platform integration.

### Changed
- Dropped Python 3.9 support, setting the minimum required version to 3.10.
- Pinned development dependency versions for reproducible builds.
- **Dependencies**:
  - Bump `requests` from 2.32.5 to 2.33.1.
  - Bump `urllib3` from 2.5.0 to 2.6.3.
  - Bump `cryptography` from 46.0.3 to 46.0.7.

### Security
- Added input validation to ensure `folder_id` and `slug` contain only URL-safe characters.
- Prevented path traversal vulnerabilities in output filenames.

## [1.3.0] - 2026-04-08

### Added
- Added support for scraping Instapaper's special "Liked" and "Archive" collections.
- Added support for configuring the output format via a configuration file, with an option to override it using a command-line argument.
- Added a DeepWiki badge to `README.md` to provide an additional channel for user support.

### Changed
- **Dependencies**:
  - Updated `certifi` dependency.
  - Updated the `codecov/codecov-action` GitHub Action to v6.

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
