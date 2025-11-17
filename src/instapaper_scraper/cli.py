import sys
import logging
import argparse
import requests
from dotenv import load_dotenv

from . import __version__
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
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
    )
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
    parser.add_argument(
        "--session-file", help="Path to the encrypted session file."
    )
    parser.add_argument("--key-file", help="Path to the session key file.")
    args = parser.parse_args()

    # Determine output filename
    output_filename = args.output
    if not output_filename:
        ext = "db" if args.format == "sqlite" else args.format
        output_filename = f"output/bookmarks.{ext}"

    session = requests.Session()

    # 1. Authenticate
    auth_args = {}
    if args.session_file:
        auth_args["session_file"] = args.session_file
    if args.key_file:
        auth_args["key_file"] = args.key_file

    authenticator = InstapaperAuthenticator(session, **auth_args)
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
