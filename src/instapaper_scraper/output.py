import os
import json
import sqlite3
import logging
from typing import List, Dict, Any

# Constants for file operations
JSON_INDENT = 4

# Constants for CSV output
CSV_HEADER = "id,title,url\n"
CSV_DELIMITER = ","
CSV_ROW_FORMAT = "{id},{title},{url}\n"

# Constants for SQLite output
SQLITE_TABLE_NAME = "articles"
SQLITE_ID_COL = "id"
SQLITE_TITLE_COL = "title"
SQLITE_URL_COL = "url"
SQLITE_CREATE_TABLE_SQL = f"""
        CREATE TABLE IF NOT EXISTS {SQLITE_TABLE_NAME} (
            {SQLITE_ID_COL} TEXT PRIMARY KEY,
            {SQLITE_TITLE_COL} TEXT NOT NULL,
            {SQLITE_URL_COL} TEXT NOT NULL
        )
    """
SQLITE_INSERT_SQL = f"INSERT OR REPLACE INTO {SQLITE_TABLE_NAME} ({SQLITE_ID_COL}, {SQLITE_TITLE_COL}, {SQLITE_URL_COL}) VALUES (:{SQLITE_ID_COL}, :{SQLITE_TITLE_COL}, :{SQLITE_URL_COL})"

# Constants for logging messages
LOG_NO_ARTICLES = "No articles found to save."
LOG_SAVED_ARTICLES = "Saved {count} articles to {filename}"
LOG_UNKNOWN_FORMAT = "Unknown output format: {format}"


def save_to_csv(data: List[Dict[str, Any]], filename: str):
    """Saves a list of articles to a CSV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write(CSV_HEADER)
        for article in data:
            # Basic CSV quoting for titles with commas
            title = article[SQLITE_TITLE_COL]
            if CSV_DELIMITER in title:
                title = f'"{title}"'
            f.write(
                CSV_ROW_FORMAT.format(
                    id=article[SQLITE_ID_COL], title=title, url=article[SQLITE_URL_COL]
                )
            )
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_json(data: List[Dict[str, Any]], filename: str):
    """Saves a list of articles to a JSON file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=JSON_INDENT, ensure_ascii=False)
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=filename))


def save_to_sqlite(data: List[Dict[str, Any]], db_name: str):
    """Saves a list of articles to a SQLite database."""
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(SQLITE_CREATE_TABLE_SQL)
    cursor.executemany(SQLITE_INSERT_SQL, data)
    conn.commit()
    conn.close()
    logging.info(LOG_SAVED_ARTICLES.format(count=len(data), filename=db_name))


def save_articles(data: List[Dict[str, Any]], format: str, filename: str):
    """
    Dispatches to the correct save function based on the format.
    """
    if not data:
        logging.info(LOG_NO_ARTICLES)
        return

    if format == "csv":
        save_to_csv(data, filename=filename)
    elif format == "json":
        save_to_json(data, filename=filename)
    elif format == "sqlite":
        save_to_sqlite(data, db_name=filename)
    else:
        logging.error(LOG_UNKNOWN_FORMAT.format(format=format))
