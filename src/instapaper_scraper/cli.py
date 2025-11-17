import sys
import logging
import argparse
import requests
import tomli
from pathlib import Path
from dotenv import load_dotenv

from . import __version__
from .auth import InstapaperAuthenticator
from .api import InstapaperClient
from .output import save_articles
from .exceptions import ScraperStructureChanged


def load_config(config_path_str: str | None = None) -> dict | None:
    """
    Loads configuration from a TOML file.
    It checks the provided path, then ~/.config/instapaper-scraper/config.toml,
    and finally config.toml in the project root.
    """
    app_name = "instapaper-scraper"
    default_paths = [
        Path.home() / ".config" / app_name / "config.toml",
        Path("config.toml"),
    ]

    paths_to_check = []
    if config_path_str:
        paths_to_check.insert(0, Path(config_path_str).expanduser())
    paths_to_check.extend(default_paths)

    for path in paths_to_check:
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    logging.info(f"Loading configuration from {path}")
                    return tomli.load(f)
            except tomli.TOMLDecodeError as e:
                logging.error(f"Error decoding TOML file at {path}: {e}")
                return None
    return None


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
        "--config-path",
        help="Path to the configuration file.",
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
    parser.add_argument("--username", help="Instapaper username.")
    parser.add_argument("--password", help="Instapaper password.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of pages to scrape (default: unlimited)",
    )
    parser.add_argument(
        "--folder",
        help="Folder key, ID, or slug to scrape. Use 'none' to disable folder mode.",
    )
    args = parser.parse_args()

    config = load_config(args.config_path)
    folders = config.get("folders", []) if config else []
    selected_folder = None

    if args.folder:
        if args.folder.lower() == "none":
            selected_folder = None
        else:
            if not config:
                logging.error("Configuration file not found or failed to load. The --folder option requires a configuration file.")
                sys.exit(1)
            else:
                for f in folders:
                    if args.folder in (f.get("key"), str(f.get("id")), f.get("slug")):
                        selected_folder = f
                        break
                if not selected_folder:
                    # If folder is not in config, treat it as a folder ID
                    selected_folder = {"id": args.folder}
    elif folders:
        print("Available folders:")
        print("  0: none (non-folder mode)")
        for i, folder in enumerate(folders):
            display_name = folder.get("key") or folder.get("slug") or folder.get("id")
            print(f"  {i+1}: {display_name}")

        try:
            choice = int(input("Select a folder (enter a number): "))
            if 0 < choice <= len(folders):
                selected_folder = folders[choice - 1]
            elif choice != 0:
                print("Invalid selection. Continuing in non-folder mode.")
        except (ValueError, IndexError):
            print("Invalid input. Continuing in non-folder mode.")

    # Determine output filename
    output_filename = args.output
    if not output_filename:
        if selected_folder and selected_folder.get("output_filename"):
            output_filename = selected_folder["output_filename"]
        elif not selected_folder and config and config.get("output_filename"):
            output_filename = config["output_filename"]
        else:
            ext = "db" if args.format == "sqlite" else args.format
            output_filename = f"output/bookmarks.{ext}"

    session = requests.Session()

    # 1. Authenticate
    auth_args = {}
    if args.session_file:
        auth_args["session_file"] = args.session_file
    if args.key_file:
        auth_args["key_file"] = args.key_file
    if args.username:
        auth_args["username"] = args.username
    if args.password:
        auth_args["password"] = args.password

    authenticator = InstapaperAuthenticator(session, **auth_args)
    if not authenticator.login():
        sys.exit(1)  # Exit if login fails

    # 2. Scrape Articles
    client = InstapaperClient(session)
    try:
        folder_info = selected_folder if selected_folder else None
        all_articles = client.get_all_articles(limit=args.limit, folder_info=folder_info)
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
