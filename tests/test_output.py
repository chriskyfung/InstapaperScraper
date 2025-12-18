import pytest
import json
import sqlite3
import logging
import io
import csv
from instapaper_scraper.output import (
    save_to_csv,
    save_to_json,
    save_to_sqlite,
    save_articles,
)
from instapaper_scraper.constants import INSTAPAPER_READ_URL


@pytest.fixture
def sample_articles():
    """Fixture for sample article data."""

    # Return a function to allow creating a fresh copy for each test
    def _sample_articles():
        return [
            {"id": "1", "title": "Article One", "url": "http://example.com/1"},
            {
                "id": "2",
                "title": "Article Two, with comma",
                "url": "http://example.com/2",
            },
            {
                "id": "3",
                "title": 'Article Three, with "quotes"',
                "url": "http://example.com/3",
            },
        ]

    return _sample_articles


@pytest.fixture
def output_dir(tmp_path):
    """Fixture for a temporary output directory."""
    return tmp_path / "output"


def test_save_to_csv_without_instapaper_url(sample_articles, output_dir):
    """Test saving articles to a CSV file without the Instapaper URL."""
    csv_file = output_dir / "bookmarks.csv"
    articles = sample_articles()
    save_to_csv(articles, str(csv_file), add_instapaper_url=False)

    assert csv_file.exists()

    # Generate expected content
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "title", "url"],
        quoting=csv.QUOTE_ALL,
    )
    writer.writeheader()
    writer.writerows(articles)
    expected_content = output.getvalue()

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        content = f.read()
        assert content == expected_content


def test_save_to_csv_with_instapaper_url(sample_articles, output_dir):
    """Test saving articles to a CSV file with an Instapaper URL."""
    csv_file = output_dir / "bookmarks_with_prefix.csv"
    articles = sample_articles()
    for article in articles:
        article["instapaper_url"] = f"{INSTAPAPER_READ_URL}{article['id']}"

    save_to_csv(articles, str(csv_file), add_instapaper_url=True)

    assert csv_file.exists()

    # Generate expected content
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "instapaper_url", "title", "url"],
        quoting=csv.QUOTE_ALL,
    )
    writer.writeheader()
    writer.writerows(articles)
    expected_content = output.getvalue()

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        content = f.read()
        assert content == expected_content


def test_save_to_json(sample_articles, output_dir):
    """Test saving articles to a JSON file."""
    json_file = output_dir / "bookmarks.json"
    articles = sample_articles()
    save_to_json(articles, str(json_file))

    assert json_file.exists()
    with open(json_file, "r") as f:
        data = json.load(f)
        assert data == articles


def test_save_to_sqlite(sample_articles, output_dir):
    """Test saving articles to a SQLite database."""
    db_file = output_dir / "bookmarks.db"
    save_to_sqlite(sample_articles(), str(db_file), add_instapaper_url=False)

    assert db_file.exists()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url FROM articles ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 3
    assert rows[0] == ("1", "Article One", "http://example.com/1")
    assert rows[1] == ("2", "Article Two, with comma", "http://example.com/2")
    assert rows[2] == ("3", 'Article Three, with "quotes"', "http://example.com/3")


def test_save_to_sqlite_with_instapaper_url(sample_articles, output_dir):
    """Test saving articles to a SQLite database with the Instapaper URL."""
    db_file = output_dir / "bookmarks_with_instapaper_url.db"
    articles = sample_articles()
    for article in articles:
        article["instapaper_url"] = f"{INSTAPAPER_READ_URL}{article['id']}"

    save_to_sqlite(articles, str(db_file), add_instapaper_url=True)

    assert db_file.exists()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, instapaper_url, title, url FROM articles ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 3
    assert rows[0] == (
        "1",
        f"{INSTAPAPER_READ_URL}1",
        "Article One",
        "http://example.com/1",
    )
    assert rows[1] == (
        "2",
        f"{INSTAPAPER_READ_URL}2",
        "Article Two, with comma",
        "http://example.com/2",
    )
    assert rows[2] == (
        "3",
        f"{INSTAPAPER_READ_URL}3",
        'Article Three, with "quotes"',
        "http://example.com/3",
    )


@pytest.mark.parametrize("add_instapaper_url", [True, False])
@pytest.mark.parametrize(
    "format, filename",
    [("csv", "test.csv"), ("json", "test.json"), ("sqlite", "test.db")],
)
def test_save_articles_dispatcher(
    sample_articles, output_dir, format, filename, add_instapaper_url
):
    """Test the main save_articles dispatcher function."""
    output_file = output_dir / filename
    save_articles(
        sample_articles(), format, str(output_file), add_instapaper_url=add_instapaper_url
    )
    assert output_file.exists()


def test_save_articles_no_data(output_dir, caplog):
    """Test that save_articles handles empty data correctly."""
    output_file = output_dir / "bookmarks.csv"
    with caplog.at_level(logging.INFO):
        save_articles([], "csv", str(output_file))

    assert not output_file.exists()
    assert "No articles found to save." in caplog.text
