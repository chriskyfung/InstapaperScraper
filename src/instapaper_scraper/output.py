import os
import json
import sqlite3
import logging
from typing import List, Dict, Any


def save_to_csv(data: List[Dict[str, Any]], filename: str):
    """Saves a list of articles to a CSV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write("id,title,url\n")
        for article in data:
            # Basic CSV quoting for titles with commas
            title = article["title"]
            if "," in title:
                title = f'"{title}"'
            f.write(f"{article['id']},{title},{article['url']}\n")
    logging.info(f"Saved {len(data)} articles to {filename}")


def save_to_json(data: List[Dict[str, Any]], filename: str):
    """Saves a list of articles to a JSON file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logging.info(f"Saved {len(data)} articles to {filename}")


def save_to_sqlite(data: List[Dict[str, Any]], db_name: str):
    """Saves a list of articles to a SQLite database."""
    os.makedirs(os.path.dirname(db_name), exist_ok=True)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """
    )
    cursor.executemany(
        "INSERT OR REPLACE INTO articles (id, title, url) VALUES (:id, :title, :url)",
        data,
    )
    conn.commit()
    conn.close()
    logging.info(f"Saved {len(data)} articles to {db_name}")


def save_articles(data: List[Dict[str, Any]], format: str, filename: str):
    """
    Dispatches to the correct save function based on the format.
    """
    if not data:
        logging.info("No articles found to save.")
        return

    if format == "csv":
        save_to_csv(data, filename=filename)
    elif format == "json":
        save_to_json(data, filename=filename)
    elif format == "sqlite":
        save_to_sqlite(data, db_name=filename)
    else:
        logging.error(f"Unknown output format: {format}")
