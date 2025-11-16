import sys
import logging
import argparse
import requests
from dotenv import load_dotenv

from .auth import InstapaperAuthenticator
from .api import InstapaperClient
from .output import save_articles
from .exceptions import ScraperStructureChanged


def main():
    """
    Main entry point for the Instapaper scraper CLI.
    """
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Scrape Instapaper articles.")
    parser.add_argument(
        "--format",
        choices=["csv", "json", "sqlite"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. If not provided, defaults to output/bookmarks.{format}",
    )
    args = parser.parse_args()

    # Determine output filename
    output_filename = args.output
    if not output_filename:
        ext = "db" if args.format == "sqlite" else args.format
        output_filename = f"output/bookmarks.{ext}"

    session = requests.Session()

    # 1. Authenticate
    authenticator = InstapaperAuthenticator(session)
    if not authenticator.login():
        sys.exit(1)  # Exit if login fails

    # 2. Scrape Articles
    client = InstapaperClient(session)
    try:
        all_articles = client.get_all_articles()
    except ScraperStructureChanged as e:
        logging.error(f"Stopping scraper due to an unrecoverable error: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logging.error(f"An HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}")
        sys.exit(1)

    # 3. Save Articles
    save_articles(all_articles, args.format, output_filename)


if __name__ == "__main__":
    main()
