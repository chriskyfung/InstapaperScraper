# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [1.1.1] - 2023-03-07

### Changed
- Updated various dependencies to their latest versions.

## [1.1.0] - 2023-03-06

### Added
- Added Dependabot and funding configuration files.

### Fixed
- Addressed an issue with handling non-200 status codes during scraping.
- Corrected a boolean conversion error.

### Changed
- Implemented a new transactional pattern for scraping.
- Pinned `guara` dependency to a specific version.

## [1.0.0] - 2023-03-05

### Added
- Introduced support for scraping articles from specific Instapaper folders.

### Changed
- Removed unused functions and cleaned up imports for a more efficient codebase.

### Chore
- Added an example environment configuration file.
- Updated the `README.md` to reflect new features like CSV export and folder mode.
