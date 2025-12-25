import pytest
import logging
import requests
from unittest.mock import MagicMock, patch
from pathlib import Path
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


def test_cli_successful_run(mock_auth, mock_client, mock_save, monkeypatch, caplog):
    """Test a successful run of the CLI with default arguments."""
    mock_auth.return_value.login.return_value = True
    mock_articles = [{"id": "1", "title": "Test", "url": "http://test.com"}]
    mock_client.return_value.get_all_articles.return_value = mock_articles
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])
    # Mock CONFIG_DIR and CONFIG_FILENAME to ensure no config file is found
    monkeypatch.setattr("instapaper_scraper.cli.CONFIG_DIR", Path("/non/existent/dir"))
    monkeypatch.setattr(
        "instapaper_scraper.cli.CONFIG_FILENAME", "non_existent_config.toml"
    )

    with caplog.at_level(logging.INFO):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_auth.assert_called_once()
    mock_auth.return_value.login.assert_called_once()
    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )
    mock_save.assert_called_once_with(
        mock_articles, "csv", "output/bookmarks.csv", add_instapaper_url=False
    )
    assert "No configuration file found at any default location." in caplog.text
    assert "Articles scraped and saved successfully." in caplog.text


def test_cli_login_failure(mock_auth, mock_client, mock_save, monkeypatch, capsys):
    """Test that the CLI exits if login fails."""
    mock_auth.return_value.login.return_value = False
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with pytest.raises(SystemExit) as e:
            with patch("builtins.input", return_value="0"):
                cli.main()

    assert e.value.code == 1
    mock_client.return_value.get_all_articles.assert_not_called()
    mock_save.assert_not_called()


@pytest.mark.parametrize("format, expected_ext", [("json", "json"), ("sqlite", "db")])
def test_cli_custom_format(
    mock_auth,
    mock_client,
    mock_save,
    monkeypatch,
    format,
    expected_ext,
):
    """Test the CLI with custom format arguments."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--format", format])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    expected_filename = f"output/bookmarks.{expected_ext}"
    mock_save.assert_called_once_with(
        [], format, expected_filename, add_instapaper_url=False
    )


def test_cli_custom_output_file(mock_auth, mock_client, mock_save, monkeypatch):
    """Test the CLI with a custom output file argument."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    custom_file = "my_special_bookmarks.json"
    monkeypatch.setattr(
        "sys.argv", ["instapaper-scraper", "--format", "json", "-o", custom_file]
    )

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once_with([], "json", custom_file, add_instapaper_url=False)


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

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    # The authenticator should be called with Path objects
    called_kwargs = mock_auth.call_args[1]
    assert called_kwargs.get("session_file") == Path(session_file)
    assert called_kwargs.get("key_file") == Path(key_file)


def test_cli_custom_credentials(mock_auth, mock_client, mock_save, monkeypatch):
    """Test that custom username and password are passed to the authenticator."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    username = "cli_user"
    password = "cli_password"
    monkeypatch.setattr(
        "sys.argv",
        ["instapaper-scraper", "--username", username, "--password", password],
    )

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    called_kwargs = mock_auth.call_args.kwargs
    assert called_kwargs.get("username") == username
    assert called_kwargs.get("password") == password


def test_cli_with_add_instapaper_url(mock_auth, mock_client, mock_save, monkeypatch):
    """Test that the --add-instapaper-url argument triggers the read URL prefix."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--add-instapaper-url"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_save.assert_called_once_with(
        [], "csv", "output/bookmarks.csv", add_instapaper_url=True
    )


def test_cli_with_limit(mock_auth, mock_client, mock_save, monkeypatch):
    """Test that the --limit argument is passed to the client."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--limit", "5"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=5, folder_info=None
    )


def test_cli_scraper_exception(mock_auth, mock_client, monkeypatch, caplog):
    """Test that the CLI handles exceptions from the scraper client."""
    from instapaper_scraper.exceptions import ScraperStructureChanged

    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.side_effect = ScraperStructureChanged(
        "HTML changed"
    )
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with pytest.raises(SystemExit) as e:
            with patch("builtins.input", return_value="0"):
                cli.main()

    assert e.value.code == 1
    assert "Stopping scraper due to an unrecoverable error: HTML changed" in caplog.text


@pytest.mark.parametrize("version_flag", ["--version", "-v"])
def test_cli_version_flag(monkeypatch, capsys, version_flag):
    """Test that the CLI prints the version and exits."""
    # Mocking __version__ in instapaper_scraper.cli since it's already imported
    monkeypatch.setattr("instapaper_scraper.cli.__version__", "1.0.0")
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", version_flag])

    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "instapaper-scraper" in captured.out
    assert "1.0.0" in captured.out


def test_cli_with_config_interactive_selection(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test interactive folder selection with a config file."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    folder_config = {"key": "ml", "id": "12345", "slug": "machine-learning"}
    config = {"folders": [folder_config]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="1"):
            cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=folder_config
    )


def test_cli_with_config_folder_argument(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test selecting a folder via the --folder argument."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    folder_config = {"key": "ml", "id": "12345", "slug": "machine-learning"}
    config = {"folders": [folder_config]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--folder", "ml"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=folder_config
    )


def test_cli_with_config_folder_output_preset(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test using the output filename preset from the config."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {
        "folders": [
            {
                "key": "ml",
                "id": "12345",
                "slug": "machine-learning",
                "output_filename": "ml-articles.json",
            },
        ]
    }
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--folder", "ml"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        cli.main()

    mock_save.assert_called_once_with(
        [], "csv", "ml-articles.json", add_instapaper_url=False
    )


def test_cli_folder_none_with_config_output(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test --folder=none with a top-level output_filename in config."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"output_filename": "home.csv"}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--folder", "none"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )
    mock_save.assert_called_once_with([], "csv", "home.csv", add_instapaper_url=False)


def test_cli_no_folder_with_config_output(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test non-folder mode with a top-level output_filename in config."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"output_filename": "home.csv", "folders": []}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )
    mock_save.assert_called_once_with([], "csv", "home.csv", add_instapaper_url=False)


def test_cli_folder_argument_no_config_exits(
    mock_auth, mock_client, mock_save, monkeypatch, caplog
):
    """Test that CLI exits if --folder is used without a config file."""
    # Simulate no config loaded
    mock_load_config = MagicMock(return_value=None)
    monkeypatch.setattr("instapaper_scraper.cli.load_config", mock_load_config)
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--folder", "some-folder"])

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as e:
            cli.main()

    assert e.value.code == 1
    assert (
        "Configuration file not found or failed to load. The --folder option requires a configuration file."
        in caplog.text
    )
    mock_auth.assert_not_called()
    mock_client.assert_not_called()
    mock_save.assert_not_called()


def test_resolve_path_with_arg():
    """Test _resolve_path when an argument path is provided."""
    arg_path = "/tmp/custom_path"
    result = cli._resolve_path(arg_path, "working.file", Path("/home/user/config.file"))
    assert result == Path(arg_path)


def test_resolve_path_working_dir_exists(tmp_path, monkeypatch):
    """Test _resolve_path when working directory file exists."""
    working_file = tmp_path / "working.file"
    working_file.write_text("content")

    # Change current working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    result = cli._resolve_path(None, "working.file", Path("/home/user/config.file"))
    assert result == Path("working.file")


def test_resolve_path_default_to_user_dir():
    """Test _resolve_path when no arg and no working dir file exists."""
    user_dir_file = Path("/home/user/config.file")
    result = cli._resolve_path(None, "non_existent.file", user_dir_file)
    assert result == user_dir_file


def test_resolve_path_user_dir_path_is_none():
    """Test _resolve_path when user_config_dir_path is None and no other path is found."""
    result = cli._resolve_path(None, "non_existent.file", None)
    assert result is None


def test_resolve_path_working_dir_file_does_not_exist(tmp_path, monkeypatch):
    """Test _resolve_path when working directory file does not exist, and it falls back."""
    # Ensure current working directory is tmp_path
    monkeypatch.chdir(tmp_path)
    user_dir_file = Path("/home/user/config.file")
    result = cli._resolve_path(None, "non_existent.file", user_dir_file)
    assert result == user_dir_file


def test_load_config_invalid_toml(tmp_path, caplog):
    """Test load_config with an invalid TOML file."""
    invalid_toml = tmp_path / "invalid.toml"
    invalid_toml.write_text("invalid = {")

    with caplog.at_level(logging.ERROR):
        result = cli.load_config(str(invalid_toml))

    assert result is None
    assert f"Error decoding TOML file at {invalid_toml}" in caplog.text


def test_load_config_not_found(caplog, monkeypatch):
    """Test load_config when no config file is found."""
    # Mock CONFIG_DIR to point to a non-existent directory to avoid loading ~/.config/...
    monkeypatch.setattr("instapaper_scraper.cli.CONFIG_DIR", Path("/non/existent/dir"))
    # Also ensure current directory config doesn't exist or isn't used
    monkeypatch.setattr(
        "instapaper_scraper.cli.CONFIG_FILENAME", "non_existent_config.toml"
    )

    with caplog.at_level(logging.INFO):
        # Use a path that definitely doesn't exist
        result = cli.load_config("/non/existent/path/to/config.toml")

    assert result is None
    assert "No configuration file found at any default location." in caplog.text


def test_load_config_from_args_config_file(tmp_path):
    """Test load_config when a config file is provided via args.config_file."""
    config_content = "[folders]\nkey = 'test'"
    config_file = tmp_path / "custom_config.toml"
    config_file.write_text(config_content)

    result = cli.load_config(str(config_file))
    assert result == {"folders": {"key": "test"}}


def test_load_config_empty_toml(tmp_path):
    """Test load_config with an empty but valid TOML file."""
    empty_toml = tmp_path / "empty.toml"
    empty_toml.write_text("")

    result = cli.load_config(str(empty_toml))
    assert result == {}


def test_cli_folder_id_not_in_config(mock_auth, mock_client, mock_save, monkeypatch):
    """Test providing a folder ID that is not in the config."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"folders": [{"key": "other", "id": "999"}]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper", "--folder", "12345"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info={"id": "12345"}
    )


def test_cli_interactive_invalid_input(mock_auth, mock_client, mock_save, monkeypatch):
    """Test interactive selection with invalid input (non-integer)."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"folders": [{"key": "ml", "id": "12345"}]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="invalid"):
            cli.main()

    # Should default to non-folder mode
    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )


def test_cli_interactive_out_of_range(mock_auth, mock_client, mock_save, monkeypatch):
    """Test interactive selection with out of range integer."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"folders": [{"key": "ml", "id": "12345"}]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="5"):
            cli.main()

    # Should default to non-folder mode
    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )


def test_cli_interactive_empty_folder_list(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test interactive selection when the config's folders list is empty."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    config = {"folders": []}  # Empty folders list
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        # input() should not be called as there are no folders to choose from
        cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )
    mock_save.assert_called_once_with(
        [], "csv", "output/bookmarks.csv", add_instapaper_url=False
    )


def test_cli_interactive_select_no_folder(
    mock_auth, mock_client, mock_save, monkeypatch
):
    """Test interactive selection where user chooses '0' for no folder."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    folder_config = {"key": "ml", "id": "12345", "slug": "machine-learning"}
    config = {"folders": [folder_config]}
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value=config):
        with patch("builtins.input", return_value="0"):  # User selects '0'
            cli.main()

    mock_client.return_value.get_all_articles.assert_called_once_with(
        limit=None, folder_info=None
    )
    mock_save.assert_called_once_with(
        [], "csv", "output/bookmarks.csv", add_instapaper_url=False
    )


def test_cli_http_error(mock_auth, mock_client, monkeypatch, caplog):
    """Test that the CLI handles requests.exceptions.RequestException."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.side_effect = (
        requests.exceptions.RequestException("Connection error")
    )
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with pytest.raises(SystemExit) as e:
            cli.main()

    assert e.value.code == 1
    assert "An HTTP error occurred: Connection error" in caplog.text


def test_cli_unexpected_error(mock_auth, mock_client, monkeypatch, caplog):
    """Test that the CLI handles unexpected exceptions."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.side_effect = Exception("Boom!")
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with pytest.raises(SystemExit) as e:
            cli.main()

    assert e.value.code == 1
    assert "An unexpected error occurred during scraping: Boom!" in caplog.text


def test_cli_save_articles_exception(
    mock_auth, mock_client, mock_save, monkeypatch, caplog
):
    """Test that a generic exception in save_articles is caught."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = [{"id": "1"}]
    mock_save.side_effect = Exception("Something broke")
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])

    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with pytest.raises(SystemExit) as e:
            cli.main()

    assert e.value.code == 1
    assert "An unexpected error occurred during saving: Something broke" in caplog.text


def test_cli_main_block_execution():
    """Test the 'if __name__ == "__main__":' block."""

    # We use a trick to cover the 'if __name__ == "__main__":' block
    # without actually running main() which is hard to mock correctly in that context.
    # By using exec on the last few lines of the file.
    import inspect

    lines = inspect.getsourcelines(cli)[0]
    # Find the line 'if __name__ == "__main__":'
    try:
        start_index = next(
            i for i, line in enumerate(lines) if 'if __name__ == "__main__":' in line
        )
        block = "".join(lines[start_index:])
        # Mock main to avoid actual execution
        with patch("instapaper_scraper.cli.main") as mock_main:
            exec(block, {"__name__": "__main__", "main": mock_main})
            mock_main.assert_called_once()
    except StopIteration:
        pytest.fail("Could not find __main__ block in cli.py")
