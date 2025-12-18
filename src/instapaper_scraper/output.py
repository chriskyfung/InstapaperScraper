import os
import json
import sqlite3
import logging
import csv
from typing import List, Dict, Any

from .constants import INSTAPAPER_READ_URL

# Constants for file operations
JSON_INDENT = 4

# Constants for SQLite output
SQLITE_TABLE_NAME = "articles"
SQLITE_ID_COL = "id"
SQLITE_INSTAPAPER_URL_COL = "instapaper_url"
SQLITE_TITLE_COL = "title"
SQLITE_URL_COL = "url"

# Constants for logging messages
LOG_NO_ARTICLES = "No articles found to save."
LOG_SAVED_ARTICLES = "Saved {count} articles to {filename}"
LOG_UNKNOWN_FORMAT = "Unknown output format: {format}"


def get_sqlite_create_table_sql(add_instapaper_url: bool = False) -> str:
    """Returns the SQL statement to create the articles table."""
    columns = [
        f"{SQLITE_ID_COL} TEXT PRIMARY KEY",
        f"{SQLITE_TITLE_COL} TEXT NOT NULL",
        f"{SQLITE_URL_COL} TEXT NOT NULL",
    ]
    if add_instapaper_url:
        columns.append(
            f"{SQLITE_INSTAPAPER_URL_COL} TEXT GENERATED ALWAYS AS ('{INSTAPAPER_READ_URL}' || {SQLITE_ID_COL}) VIRTUAL"
        )
    return f"CREATE TABLE IF NOT EXISTS {SQLITE_TABLE_NAME} ({', '.join(columns)})"


def get_sqlite_insert_sql() -> str:
    """Returns the SQL statement to insert an article."""
    cols = [SQLITE_ID_COL, SQLITE_TITLE_COL, SQLITE_URL_COL]
    placeholders = [f":{SQLITE_ID_COL}", f":{SQLITE_TITLE_COL}", f":{SQLITE_URL_COL}"]
    return f"INSERT OR REPLACE INTO {SQLITE_TABLE_NAME} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"


def save_to_csv(data: List[Dict[str, Any]], filename: str, add_instapaper_url: bool = False):
    """Saves a list of articles to a CSV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        if add_instapaper_url:
            fieldnames = [
                SQLITE_ID_COL,
                SQLITE_INSTAPAPER_URL_COL,
                SQLITE_TITLE_COL,
                SQLITE_URL_COL,
            ]
        else:
            fieldnames = [SQLITE_ID_COL, SQLITE_TITLE_COL, SQLITE_URL_COL]

        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)

    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_json(data: List[Dict[str, Any]], filename: str):
    """Saves a list of articles to a JSON file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=JSON_INDENT, ensure_ascii=False)
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_sqlite(
    data: List[Dict[str, Any]], db_name: str, add_instapaper_url: bool = False
):
    """Saves a list of articles to a SQLite database."""
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(get_sqlite_create_table_sql(add_instapaper_url))
    cursor.executemany(get_sqlite_insert_sql(), data)
    conn.commit()
    conn.close()
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=db_name))


def save_articles(
    data: List[Dict[str, Any]],
    format: str,
    filename: str,
    add_instapaper_url: bool = False,
):
    """
    Dispatches to the correct save function based on the format.
    """
    if not data:
        logging.info(LOG_NO_ARTICLES)
        return

    if add_instapaper_url:
        data = [
            {**article, SQLITE_INSTAPAPER_URL_COL: f"{INSTAPAPER_READ_URL}{article[SQLITE_ID_COL]}"}
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
