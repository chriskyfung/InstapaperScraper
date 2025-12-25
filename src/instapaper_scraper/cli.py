import sys
import logging
import argparse
import requests
from pathlib import Path
from typing import Union, List, Dict, Any, Optional, cast

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from . import __version__
from .auth import InstapaperAuthenticator
from .api import InstapaperClient
from .output import save_articles
from .exceptions import ScraperStructureChanged
from .constants import CONFIG_DIR

# --- Constants ---
CONFIG_FILENAME = "config.toml"
DEFAULT_SESSION_FILENAME = ".instapaper_session"
DEFAULT_KEY_FILENAME = ".session_key"
DEFAULT_OUTPUT_FILENAME = "output/bookmarks.{ext}"


def _resolve_path(
    arg_path: str, working_dir_filename: str, user_dir_filename: Path
) -> Path:
    """Resolves a path based on CLI arg, working dir, and user config dir."""
    if arg_path:
        return Path(arg_path).expanduser()

    working_dir_path = Path(working_dir_filename)
    if working_dir_path.exists():
        logging.info(f"Found {working_dir_filename} in working directory.")
        return working_dir_path

    return user_dir_filename


def load_config(config_path_str: Union[str, None] = None) -> Optional[Dict[str, Any]]:
    """
    Loads configuration from a TOML file.
    It checks the provided path, then config.toml in the project root,
    and finally ~/.config/instapaper-scraper/config.toml.
    """
    default_paths = [
        Path(CONFIG_FILENAME),
        CONFIG_DIR / CONFIG_FILENAME,
    ]

    paths_to_check: List[Path] = []
    if config_path_str:
        paths_to_check.insert(0, Path(config_path_str).expanduser())
    paths_to_check.extend(default_paths)

    for path in paths_to_check:
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    logging.info(f"Loading configuration from {path}")
                    return cast(Dict[str, Any], tomllib.load(f))
            except tomllib.TOMLDecodeError as e:
                logging.error(f"Error decoding TOML file at {path}: {e}")
                return None
    logging.info("No configuration file found at any default location.")
    return None


def main() -> None:
    """
    Main entry point for the Instapaper scraper CLI.
    """
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
    parser.add_argument("--session-file", help="Path to the encrypted session file.")
    parser.add_argument("--key-file", help="Path to the session key file.")
    parser.add_argument("--username", help="Instapaper username.")
    parser.add_argument("--password", help="Instapaper password.")
    parser.add_argument(
        "--add-instapaper-url",
        action="store_true",
        help="Add an 'instapaper_url' column to the output with the full Instapaper read URL.",
    )
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
                logging.error(
                    "Configuration file not found or failed to load. The --folder option requires a configuration file."
                )
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
            print(f"  {i + 1}: {display_name}")

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
            output_filename = DEFAULT_OUTPUT_FILENAME.format(ext=ext)

    session = requests.Session()

    # Resolve session and key file paths
    session_file = _resolve_path(
        args.session_file,
        DEFAULT_SESSION_FILENAME,
        CONFIG_DIR / DEFAULT_SESSION_FILENAME,
    )
    key_file = _resolve_path(
        args.key_file,
        DEFAULT_KEY_FILENAME,
        CONFIG_DIR / DEFAULT_KEY_FILENAME,
    )

    # 1. Authenticate
    authenticator = InstapaperAuthenticator(
        session,
        session_file=session_file,
        key_file=key_file,
        username=args.username,
        password=args.password,
    )
    if not authenticator.login():
        sys.exit(1)  # Exit if login fails

    # 2. Scrape Articles
    client = InstapaperClient(session)
    try:
        folder_info = selected_folder if selected_folder else None
        all_articles = client.get_all_articles(
            limit=args.limit, folder_info=folder_info
        )
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
    try:
        save_articles(
            all_articles,
            args.format,
            output_filename,
            add_instapaper_url=args.add_instapaper_url,
        )
        logging.info("Articles scraped and saved successfully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during saving: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
