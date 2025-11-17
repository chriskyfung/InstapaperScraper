import pytest
from unittest.mock import MagicMock

from instapaper_scraper import cli


@pytest.fixture
def mock_auth(monkeypatch):
    """Fixture to mock the InstapaperAuthenticator."""
    mock = MagicMock()
    monkeypatch.setattr("instapaper_scraper.cli.InstapaperAuthenticator", mock)
    return mock


@pytest.fixture
def mock_client(monkeypatch):
    """Fixture to mock the InstapaperClient."""
    mock = MagicMock()
    monkeypatch.setattr("instapaper_scraper.cli.InstapaperClient", mock)
    return mock


@pytest.fixture
def mock_save(monkeypatch):
    """Fixture to mock the save_articles function."""
    mock = MagicMock()
    monkeypatch.setattr("instapaper_scraper.cli.save_articles", mock)
    return mock


def test_cli_successful_run(mock_auth, mock_client, mock_save, monkeypatch):
    """Test a successful run of the CLI with default arguments."""
    # --- Arrange ---
    # Mock successful login
    mock_auth.return_value.login.return_value = True

    # Mock successful scraping
    mock_articles = [{"id": "1", "title": "Test", "url": "http://test.com"}]
    mock_client.return_value.get_all_articles.return_value = mock_articles

    # Patch sys.argv to simulate command-line arguments
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    # --- Act ---
    cli.main()

    # --- Assert ---
    # Authenticator was called
    mock_auth.assert_called_once()
    mock_auth.return_value.login.assert_called_once()

    # Client was called
    mock_client.return_value.get_all_articles.assert_called_once()

    # Save was called with the correct data and default arguments
    mock_save.assert_called_once_with(
        mock_articles,
        "csv",  # default format
        "output/bookmarks.csv",  # default filename
    )


def test_cli_login_failure(mock_auth, mock_client, mock_save, monkeypatch, capsys):
    """Test that the CLI exits if login fails."""
    # Mock failed login
    mock_auth.return_value.login.return_value = False
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 1

    # Client and save should not be called
    mock_client.return_value.get_all_articles.assert_not_called()
    mock_save.assert_not_called()


@pytest.mark.parametrize("format, expected_ext", [("json", "json"), ("sqlite", "db")])
def test_cli_custom_format(
    mock_auth, mock_client, mock_save, monkeypatch, format, expected_ext
):
    """Test the CLI with custom format arguments."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []

    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--format", format])

    cli.main()

    expected_filename = f"output/bookmarks.{expected_ext}"
    mock_save.assert_called_once_with([], format, expected_filename)


def test_cli_custom_output_file(mock_auth, mock_client, mock_save, monkeypatch):
    """Test the CLI with a custom output file argument."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []

    custom_file = "my_special_bookmarks.json"
    monkeypatch.setattr(
        "sys.argv", ["instapaper-scraper", "--format", "json", "-o", custom_file]
    )

    cli.main()

    mock_save.assert_called_once_with([], "json", custom_file)


def test_cli_custom_auth_files(mock_auth, mock_client, mock_save, monkeypatch):
    """Test that custom session and key files are passed to the authenticator."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []

    session_file = "my_session.file"
    key_file = "my_key.file"

    monkeypatch.setattr(
        "sys.argv",
        [
            "instapaper-scraper",
            "--session-file",
            session_file,
            "--key-file",
            key_file,
        ],
    )

    cli.main()

    # Check that the authenticator was initialized with the custom file paths
    mock_auth.assert_called_once()
    # The first positional argument is the session object
    # The keyword arguments are what we are interested in
    called_kwargs = mock_auth.call_args.kwargs
    assert called_kwargs.get("session_file") == session_file
    assert called_kwargs.get("key_file") == key_file


def test_cli_scraper_exception(mock_auth, mock_client, monkeypatch, caplog):
    """Test that the CLI handles exceptions from the scraper client."""
    from instapaper_scraper.exceptions import ScraperStructureChanged

    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.side_effect = ScraperStructureChanged(
        "HTML changed"
    )

    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 1
    assert "Stopping scraper due to an unrecoverable error: HTML changed" in caplog.text


@pytest.mark.parametrize("version_flag", ["--version", "-v"])
def test_cli_version_flag(monkeypatch, capsys, version_flag):
    """Test that the CLI prints the version and exits."""
    # --- Arrange ---
    # Mock the __version__ to a known value
    monkeypatch.setattr("instapaper_scraper.__version__", "2.0.0")
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", version_flag])

    # --- Act & Assert ---
    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 0  # Successful exit

    captured = capsys.readouterr()
    assert "instapaper-scraper 2.0.0" in captured.out
