import os
import logging
from typing import List, Dict, Any, TYPE_CHECKING

from .constants import INSTAPAPER_READ_URL, KEY_ID, KEY_TITLE, KEY_URL

# Constants for file operations
JSON_INDENT = 4

# Constants for SQLite output
SQLITE_TABLE_NAME = "articles"
SQLITE_INSTAPAPER_URL_COL = "instapaper_url"

# Constants for logging messages
LOG_NO_ARTICLES = "No articles found to save."
LOG_SAVED_ARTICLES = "Saved {count} articles to {filename}"
LOG_UNKNOWN_FORMAT = "Unknown output format: {format}"

if TYPE_CHECKING:
    # Import for type-checking purposes, and use an alias
    # to signal to linters like ruff that it is being used.
    import sqlite3 as sqlite3

    __all__ = ["sqlite3"]


def get_sqlite_create_table_sql(add_instapaper_url: bool = False) -> str:
    """Returns the SQL statement to create the articles table."""
    columns = [
        f"{KEY_ID} TEXT PRIMARY KEY",
        f"{KEY_TITLE} TEXT NOT NULL",
        f"{KEY_URL} TEXT NOT NULL",
    ]
    if add_instapaper_url:
        import sqlite3

        # The GENERATED ALWAYS AS syntax was added in SQLite 3.31.0
        if sqlite3.sqlite_version_info >= (3, 31, 0):
            columns.append(
                f"{SQLITE_INSTAPAPER_URL_COL} TEXT GENERATED ALWAYS AS ('{INSTAPAPER_READ_URL}' || {KEY_ID}) VIRTUAL"
            )
        else:
            columns.append(f"{SQLITE_INSTAPAPER_URL_COL} TEXT")

    return f"CREATE TABLE IF NOT EXISTS {SQLITE_TABLE_NAME} ({', '.join(columns)})"


def get_sqlite_insert_sql(add_instapaper_url_manually: bool = False) -> str:
    """Returns the SQL statement to insert an article."""
    cols = [KEY_ID, KEY_TITLE, KEY_URL]
    placeholders = [f":{KEY_ID}", f":{KEY_TITLE}", f":{KEY_URL}"]

    if add_instapaper_url_manually:
        cols.append(SQLITE_INSTAPAPER_URL_COL)
        placeholders.append(f":{SQLITE_INSTAPAPER_URL_COL}")

    return f"INSERT OR REPLACE INTO {SQLITE_TABLE_NAME} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"


def save_to_csv(
    data: List[Dict[str, Any]], filename: str, add_instapaper_url: bool = False
) -> None:
    """Saves a list of articles to a CSV file."""
    import csv

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        fieldnames = [KEY_ID, KEY_TITLE, KEY_URL]
        if add_instapaper_url:
            # Insert instapaper_url after the id column
            fieldnames.insert(1, SQLITE_INSTAPAPER_URL_COL)

        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)

    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_json(data: List[Dict[str, Any]], filename: str) -> None:
    """Saves a list of articles to a JSON file."""
    import json

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=JSON_INDENT, ensure_ascii=False)
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_sqlite(
    data: List[Dict[str, Any]], db_name: str, add_instapaper_url: bool = False
) -> None:
    """Saves a list of articles to a SQLite database."""
    import sqlite3

    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(get_sqlite_create_table_sql(add_instapaper_url))

    # For older SQLite versions, we need to manually add the URL
    manual_insert_required = add_instapaper_url and sqlite3.sqlite_version_info < (
        3,
        31,
        0,
    )
    if manual_insert_required:
        data_to_insert = [
            {
                **article,
                SQLITE_INSTAPAPER_URL_COL: f"{INSTAPAPER_READ_URL}{article[KEY_ID]}",
            }
            for article in data
        ]
    else:
        data_to_insert = data

    insert_sql = get_sqlite_insert_sql(
        add_instapaper_url_manually=manual_insert_required
    )
    cursor.executemany(insert_sql, data_to_insert)

    conn.commit()
    conn.close()
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=db_name))


def _correct_ext(filename: str, format: str) -> str:
    """Corrects the filename extension based on the specified format."""
    extension_map = {
        "csv": ".csv",
        "json": ".json",
        "sqlite": ".db",
    }
    if format in extension_map:
        name, _ = os.path.splitext(filename)
        return name + extension_map[format]
    return filename


def save_articles(
    data: List[Dict[str, Any]],
    format: str,
    filename: str,
    add_instapaper_url: bool = False,
) -> None:
    """
    Dispatches to the correct save function based on the format.
    """
    if not data:
        logging.info(LOG_NO_ARTICLES)
        return

    filename = _correct_ext(filename, format)

    # Add the instapaper_url to the data for formats that don't auto-generate it
    if add_instapaper_url and format in ("csv", "json"):
        data = [
            {
                **article,
                SQLITE_INSTAPAPER_URL_COL: f"{INSTAPAPER_READ_URL}{article[KEY_ID]}",
            }
            for article in data
        ]

    if format == "csv":
        save_to_csv(data, filename=filename, add_instapaper_url=add_instapaper_url)
    elif format == "json":
        save_to_json(data, filename=filename)
    elif format == "sqlite":
        save_to_sqlite(data, db_name=filename, add_instapaper_url=add_instapaper_url)
    else:
        logging.error(LOG_UNKNOWN_FORMAT.format(format=format))
