# Contributing to Instapaper Scraper

First off, thank you for considering contributing to Instapaper Scraper! It's people like you that make the open-source community such a fantastic place. Every contribution, whether it's code, documentation, or financial support, is highly valued.

## Table of Contents

- [Financial Contributions](#financial-contributions)
- [Code Contributions](#code-contributions)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Request Process](#pull-request-process)
- [Styleguides](#styleguides)

## Financial Contributions

Maintaining and developing an open-source project takes time and resources. If you find `Instapaper Scraper` useful, please consider supporting its development. This allows us to dedicate more time to new features, bug fixes, and user support.

You can support the project through the following platforms:

- **[Sponsor on GitHub](https://github.com/sponsors/chriskyfung):** Ideal for recurring monthly support. Tiers with special rewards are available!
- **[Buy Me a Coffee](https://www.buymeacoffee.com/chriskyfung):** The best option for a one-time donation.

## Code Contributions

We welcome code contributions, from simple bug fixes to new features.

### Reporting Bugs

If you encounter a bug, please [open an issue](https://github.com/chriskyfung/InstapaperScraper/issues) on our GitHub repository. A great bug report includes:

- A clear and descriptive title.
- A step-by-step description of how to reproduce the issue.
- The version of `instapaper-scraper` you are using.
- Any error messages or logs.

### Suggesting Enhancements

If you have an idea for a new feature or an improvement to an existing one, please [open an issue](https://github.com/chriskyfung/InstapaperScraper/issues) and use the "Feature Request" template. This allows us to track and discuss the proposal before any development work begins.

### Your First Code Contribution

Unsure where to start? Look for issues tagged with `good first issue` or `help wanted`. These are typically well-defined and a great way to get familiar with the codebase.

### Pull Request Process

1.  **Fork the repository** and create your branch from `master`.
2.  **Set up your development environment.** Instructions are in the `README.md` under the "Development & Testing" section. Don't forget to run `pre-commit install` after installing dev dependencies.
3.  **Make your changes.** Ensure you add or update tests as appropriate.
4.  **Ensure the test suite passes** by running `pytest`.
5.  **Format your code** with `ruff format .`, check for linting issues with `ruff check .`, run static type checks with `mypy src`, and verify license compliance with `licensecheck --fail-licenses GPL-3.0 --zero`.
6.  **Commit your changes** with a clear and concise commit message. Pre-commit hooks will automatically run `ruff` and `mypy`.
7.  **Push your branch** to your fork and submit a pull request to the main repository.

## Styleguides

- **Code:** We use `ruff` for consistent code formatting and linting, `mypy` for static type checking, and `licensecheck` for license compliance. Pre-commit hooks are configured to run some of these tools automatically.
- **Git Commit Messages:** Please follow conventional commit standards if possible, but a clear, descriptive message is the most important thing.

Thank you again for your interest in contributing!
