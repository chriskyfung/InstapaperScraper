import pytest
import json
import sqlite3
import logging
from instapaper_scraper.output import (
    save_to_csv,
    save_to_json,
    save_to_sqlite,
    save_articles,
)


@pytest.fixture
def sample_articles():
    """Fixture for sample article data."""
    return [
        {"id": "1", "title": "Article One", "url": "http://example.com/1"},
        {"id": "2", "title": "Article Two, with comma", "url": "http://example.com/2"},
    ]


@pytest.fixture
def output_dir(tmp_path):
    """Fixture for a temporary output directory."""
    return tmp_path / "output"


def test_save_to_csv(sample_articles, output_dir):
    """Test saving articles to a CSV file."""
    csv_file = output_dir / "bookmarks.csv"
    save_to_csv(sample_articles, str(csv_file))

    assert csv_file.exists()
    with open(csv_file, "r") as f:
        lines = f.readlines()
        assert lines[0].strip() == "id,title,url"
        assert lines[1].strip() == "1,Article One,http://example.com/1"
        assert lines[2].strip() == '2,"Article Two, with comma",http://example.com/2'


def test_save_to_json(sample_articles, output_dir):
    """Test saving articles to a JSON file."""
    json_file = output_dir / "bookmarks.json"
    save_to_json(sample_articles, str(json_file))

    assert json_file.exists()
    with open(json_file, "r") as f:
        data = json.load(f)
        assert data == sample_articles


def test_save_to_sqlite(sample_articles, output_dir):
    """Test saving articles to a SQLite database."""
    db_file = output_dir / "bookmarks.db"
    save_to_sqlite(sample_articles, str(db_file))

    assert db_file.exists()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url FROM articles ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("1", "Article One", "http://example.com/1")
    assert rows[1] == ("2", "Article Two, with comma", "http://example.com/2")


@pytest.mark.parametrize(
    "format, filename",
    [("csv", "test.csv"), ("json", "test.json"), ("sqlite", "test.db")],
)
def test_save_articles_dispatcher(sample_articles, output_dir, format, filename):
    """Test the main save_articles dispatcher function."""
    output_file = output_dir / filename
    save_articles(sample_articles, format, str(output_file))
    assert output_file.exists()


def test_save_articles_no_data(output_dir, caplog):
    """Test that save_articles handles empty data correctly."""
    output_file = output_dir / "bookmarks.csv"
    with caplog.at_level(logging.INFO):
        save_articles([], "csv", str(output_file))

    assert not output_file.exists()
    assert "No articles found to save." in caplog.text
