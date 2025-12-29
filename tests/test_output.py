import pytest
import json
import sqlite3
import logging
import io
import csv
from unittest.mock import patch, MagicMock, PropertyMock

from instapaper_scraper.output import (
    _correct_ext,
    save_to_csv,
    save_to_json,
    save_to_sqlite,
    save_articles,
    get_sqlite_create_table_sql,
    get_sqlite_insert_sql,
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


@pytest.fixture
def mock_sqlite3():
    """
    Fixture to mock the sqlite3 module for dynamic imports.
    This fixture patches sys.modules to replace the sqlite3 module with a mock.
    It yields a function that allows tests to configure the mock's version info.
    """
    with patch.dict("sys.modules", {"sqlite3": MagicMock()}) as mock_modules:
        mock_sqlite = mock_modules["sqlite3"]

        def _configure_mock(version_info):
            # Use PropertyMock to ensure the version comparison works correctly
            type(mock_sqlite).sqlite_version_info = PropertyMock(
                return_value=version_info
            )

        yield _configure_mock, mock_sqlite


class TestCorrectExt:
    @pytest.mark.parametrize(
        "filename, format, expected",
        [
            ("test.csv", "csv", "test.csv"),
            ("test.json", "json", "test.json"),
            ("test.db", "sqlite", "test.db"),
            ("test", "csv", "test.csv"),
            ("test.txt", "json", "test.json"),
            ("test.wrong", "sqlite", "test.db"),
            ("path/to/test", "csv", "path/to/test.csv"),
            ("path/to/test.txt", "json", "path/to/test.json"),
            ("test.txt", "unknown", "test.txt"),
        ],
    )
    def test_correct_ext(self, filename, format, expected):
        """Test that the extension is corrected for various formats."""
        assert _correct_ext(filename, format) == expected


def test_get_sqlite_create_table_sql_without_url():
    """Test CREATE TABLE SQL without instapaper_url."""
    sql = get_sqlite_create_table_sql(add_instapaper_url=False)
    assert "instapaper_url" not in sql


def test_get_sqlite_create_table_sql_with_url_modern_sqlite(mock_sqlite3):
    """Test CREATE TABLE SQL with instapaper_url on modern SQLite."""
    configure_mock, _ = mock_sqlite3
    configure_mock((3, 31, 0))
    sql = get_sqlite_create_table_sql(add_instapaper_url=True)
    assert "instapaper_url TEXT GENERATED ALWAYS AS" in sql


def test_get_sqlite_create_table_sql_with_url_old_sqlite(mock_sqlite3):
    """Test CREATE TABLE SQL with instapaper_url on old SQLite."""
    configure_mock, _ = mock_sqlite3
    configure_mock((3, 30, 0))
    sql = get_sqlite_create_table_sql(add_instapaper_url=True)
    assert "instapaper_url TEXT" in sql
    assert "GENERATED" not in sql


def test_get_sqlite_insert_sql_without_manual_url():
    """Test INSERT SQL without manual instapaper_url."""
    sql = get_sqlite_insert_sql(add_instapaper_url_manually=False)
    assert "instapaper_url" not in sql


def test_get_sqlite_insert_sql_with_manual_url():
    """Test INSERT SQL with manual instapaper_url."""
    sql = get_sqlite_insert_sql(add_instapaper_url_manually=True)
    assert "(id, title, url, instapaper_url)" in sql
    assert "VALUES (:id, :title, :url, :instapaper_url)" in sql


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
    # In a real scenario, the caller (save_articles) adds this dict key
    articles_with_url = [
        {**a, "instapaper_url": f"{INSTAPAPER_READ_URL}{a['id']}"} for a in articles
    ]

    save_to_csv(articles_with_url, str(csv_file), add_instapaper_url=True)

    assert csv_file.exists()

    # Generate expected content
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "instapaper_url", "title", "url"],
        quoting=csv.QUOTE_ALL,
    )
    writer.writeheader()
    writer.writerows(articles_with_url)
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
    """Test saving articles to a SQLite database without instapaper_url."""
    db_file = output_dir / "bookmarks.db"
    save_to_sqlite(sample_articles(), str(db_file), add_instapaper_url=False)

    assert db_file.exists()
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, url FROM articles ORDER BY id ASC")
    rows = cursor.fetchall()

    assert len(rows) == 3
    assert rows[0] == ("1", "Article One", "http://example.com/1")
    assert rows[1] == ("2", "Article Two, with comma", "http://example.com/2")
    assert rows[2] == ("3", 'Article Three, with "quotes"', "http://example.com/3")
    # Verify the instapaper_url column does not exist
    with pytest.raises(sqlite3.OperationalError):
        cursor.execute("SELECT instapaper_url FROM articles")

    conn.close()


def test_save_to_sqlite_with_instapaper_url_modern_sqlite(
    mock_sqlite3, sample_articles, output_dir
):
    """Test saving with instapaper_url on modern SQLite."""
    configure_mock, mock_sqlite = mock_sqlite3
    configure_mock((3, 31, 0))
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    articles = sample_articles()
    db_file = output_dir / "test.db"
    save_to_sqlite(articles, str(db_file), add_instapaper_url=True)

    # Check that CREATE TABLE uses GENERATED column
    create_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "GENERATED ALWAYS AS" in create_sql

    # Check that INSERT statement does NOT include the URL column
    insert_sql = mock_cursor.executemany.call_args_list[0][0][0]
    assert "instapaper_url" not in insert_sql

    # Check that data is NOT modified
    executed_data = mock_cursor.executemany.call_args_list[0][0][1]
    assert executed_data == articles
    assert "instapaper_url" not in executed_data[0]


def test_save_to_sqlite_with_instapaper_url_old_sqlite(
    mock_sqlite3, sample_articles, output_dir
):
    """Test saving with instapaper_url on old SQLite."""
    configure_mock, mock_sqlite = mock_sqlite3
    configure_mock((3, 30, 0))
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_sqlite.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    articles = sample_articles()
    db_file = output_dir / "test.db"
    save_to_sqlite(articles, str(db_file), add_instapaper_url=True)

    # Check that CREATE TABLE uses simple TEXT column
    create_sql = mock_cursor.execute.call_args_list[0][0][0]
    assert "instapaper_url TEXT" in create_sql
    assert "GENERATED" not in create_sql

    # Check that INSERT statement DOES include the URL column
    insert_sql = mock_cursor.executemany.call_args_list[0][0][0]
    assert "instapaper_url" in insert_sql

    # Check that data IS modified
    executed_data = mock_cursor.executemany.call_args_list[0][0][1]
    assert "instapaper_url" in executed_data[0]
    assert (
        executed_data[0]["instapaper_url"]
        == f"{INSTAPAPER_READ_URL}{articles[0]['id']}"
    )


@pytest.mark.parametrize("add_instapaper_url", [True, False])
@pytest.mark.parametrize(
    "format, expected_filename",
    [("csv", "test.csv"), ("json", "test.json"), ("sqlite", "test.db")],
)
def test_save_articles_dispatcher(
    sample_articles, output_dir, format, expected_filename, add_instapaper_url, caplog
):
    """Test the main save_articles dispatcher function."""
    output_file = output_dir / expected_filename
    with caplog.at_level(logging.INFO):
        save_articles(
            sample_articles(),
            format,
            str(output_file),
            add_instapaper_url=add_instapaper_url,
        )
    assert output_file.exists()
    assert f"Saved 3 articles to {output_file}" in caplog.text


@pytest.mark.parametrize(
    "format, initial_filename, expected_filename",
    [
        ("csv", "output.txt", "output.csv"),
        ("json", "output.csv", "output.json"),
        ("sqlite", "output", "output.db"),
    ],
)
def test_save_articles_corrects_extension(
    sample_articles, output_dir, format, initial_filename, expected_filename, caplog
):
    """Test that save_articles corrects the output file extension."""
    output_file = output_dir / initial_filename
    expected_file = output_dir / expected_filename

    with caplog.at_level(logging.INFO):
        save_articles(sample_articles(), format, str(output_file))

    assert not output_file.exists()  # The original file should not be created
    assert expected_file.exists()
    assert f"Saved 3 articles to {expected_file}" in caplog.text


def test_save_articles_no_data(output_dir, caplog):
    """Test that save_articles handles empty data correctly."""
    output_file = output_dir / "bookmarks.csv"
    with caplog.at_level(logging.INFO):
        save_articles([], "csv", str(output_file))

    assert not output_file.exists()
    assert "No articles found to save." in caplog.text


def test_save_articles_unknown_format(sample_articles, output_dir, caplog):
    """Test that save_articles logs an error for an unknown format."""
    output_file = output_dir / "bookmarks.txt"
    with caplog.at_level(logging.ERROR):
        save_articles(sample_articles(), "unknown", str(output_file))
    assert "Unknown output format: unknown" in caplog.text
    assert not output_file.exists()
