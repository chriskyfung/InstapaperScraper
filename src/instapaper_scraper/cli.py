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
from .constants import CONFIG_DIR, SUPPORTED_FORMATS

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
        choices=SUPPORTED_FORMATS,
        help="Output format (default: csv, configurable)",
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
        "--read-url",  # New, preferred flag
        "--add-instapaper-url",  # Old, for backward compatibility
        dest="add_instapaper_url",
        action=argparse.BooleanOptionalAction,
        help="Include the Instapaper read URL. Overrides config.",
    )
    parser.add_argument(
        "--article-preview",  # New, preferred flag
        "--add-article-preview",  # Old, for backward compatibility
        dest="add_article_preview",
        action=argparse.BooleanOptionalAction,
        help="Include the article preview text. Overrides config.",
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
    fields_config = config.get("fields", {}) if config else {}
    output_config = config.get("output", {}) if config else {}
    selected_folder = None

    # Resolve output format, giving CLI priority over config
    final_format = args.format or output_config.get("format", "csv")
    if final_format not in ["csv", "json", "sqlite"]:
        logging.warning(
            f"Invalid format '{final_format}' in config. Falling back to 'csv'."
        )
        final_format = "csv"

    # Resolve boolean flags, giving CLI priority over config
    final_add_instapaper_url = (
        args.add_instapaper_url
        if args.add_instapaper_url is not None
        else fields_config.get("read_url", False)
    )
    final_add_article_preview = (
        args.add_article_preview
        if args.add_article_preview is not None
        else fields_config.get("article_preview", False)
    )

    if args.folder:
        if args.folder.lower() == "none":
            selected_folder = None
        elif args.folder.lower() in ("liked", "archive"):
            selected_folder = {"id": args.folder.lower()}
        else:
            if not config:
                logging.error(
                    "Configuration file not found or failed to load. The --folder option requires a configuration file for custom folders."
                )
                sys.exit(1)

            for f in folders:
                if args.folder in (f.get("key"), str(f.get("id")), f.get("slug")):
                    selected_folder = f
                    break
            if not selected_folder:
                # If folder is not in config, treat it as a folder ID
                selected_folder = {"id": args.folder}
    elif folders:
        print("Available folders:")
        folder_choices: List[Dict[str, Any]] = [
            {"display": "__Home__ (scrape unfiled articles)", "info": None},
            {"display": "__Liked__ (scrape liked articles)", "info": {"id": "liked"}},
            {
                "display": "__Archive__ (scrape archived articles)",
                "info": {"id": "archive"},
            },
        ]
        for folder in folders:
            display_name = folder.get("key") or folder.get("slug") or folder.get("id")
            folder_choices.append({"display": display_name, "info": folder})

        for i, choice in enumerate(folder_choices):
            print(f"  {i}: {choice['display']}")

        try:
            choice_str = input(
                f"Select a folder (enter a number 0-{len(folder_choices)-1})[default: 0]: "
            )
            choice_idx = int(choice_str) if choice_str else 0
            if 0 <= choice_idx < len(folder_choices):
                selected_folder = folder_choices[choice_idx]["info"]
            else:
                print("Invalid selection. Continuing with no folder selected.")
        except (ValueError, IndexError):
            print("Invalid input. Continuing with no folder selected.")

    # Determine output filename
    output_filename = args.output
    if not output_filename:
        if config:
            folder_id = selected_folder.get("id") if selected_folder else None
            if folder_id == "liked":
                output_filename = config.get("liked_output_filename")
            elif folder_id == "archive":
                output_filename = config.get("archive_output_filename")
            elif selected_folder and "output_filename" in selected_folder:
                output_filename = selected_folder.get("output_filename")
            elif not selected_folder:
                output_filename = config.get("output_filename")

    if not output_filename:
        ext = "db" if final_format == "sqlite" else final_format
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
            limit=args.limit,
            folder_info=folder_info,
            add_article_preview=final_add_article_preview,
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
            final_format,
            output_filename,
            add_instapaper_url=final_add_instapaper_url,
            add_article_preview=final_add_article_preview,
        )
        logging.info("Articles scraped and saved successfully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during saving: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
