import pytest
import logging
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


def test_load_config_priority(monkeypatch, tmp_path):
    """Tests the loading priority for config.toml."""
    monkeypatch.chdir(tmp_path)
    
    # Create user config file
    user_home = tmp_path / "home"
    user_config_dir = user_home / ".config" / "instapaper-scraper"
    user_config_dir.mkdir(parents=True)
    (user_config_dir / "config.toml").write_text('[user_config]\nkey="user_config_value"')
    monkeypatch.setattr(Path, "home", lambda: user_home)

    # Create working directory config file
    (tmp_path / "config.toml").write_text('[working_dir_config]\nkey="working_dir_value"')
    
    # Case 1: No arg, should load from working directory
    config = cli.load_config()
    assert config.get("working_dir_config", {}).get("key") == "working_dir_value"
    
    # Create CLI specified config file
    cli_arg_config_path = tmp_path / "cli_arg_config.toml"
    cli_arg_config_path.write_text('[cli_config]\nkey="cli_value"')

    # Case 2: With CLI arg, should load from specified path
    config = cli.load_config(str(cli_arg_config_path))
    assert config.get("cli_config", {}).get("key") == "cli_value"

    # Case 3: No arg and no working dir file, should load from user config
    (tmp_path / "config.toml").unlink() # Remove working dir config
    config = cli.load_config()
    assert config.get("user_config", {}).get("key") == "user_config_value"

def test_session_file_resolution_priority(mock_auth, mock_client, mock_save, monkeypatch, tmp_path):
    """Tests the resolution priority for session and key files."""
    mock_auth.return_value.login.return_value = True
    mock_client.return_value.get_all_articles.return_value = []
    
    monkeypatch.chdir(tmp_path)
    
    # Setup all possible file locations
    user_home = tmp_path / "home"
    user_config_dir = user_home / ".config" / "instapaper-scraper"
    user_config_dir.mkdir(parents=True)
    (user_config_dir / ".instapaper_session").touch()
    (user_config_dir / ".session_key").touch()
    
    (tmp_path / ".instapaper_session").touch()
    (tmp_path / ".session_key").touch()
    
    cli_session_path = tmp_path / "cli_session.file"
    cli_key_path = tmp_path / "cli_key.file"
    cli_session_path.touch()
    cli_key_path.touch()
    
    monkeypatch.setattr(Path, "home", lambda: user_home)
    
    # Case 1: CLI arguments provided
    monkeypatch.setattr("sys.argv", [
        "instapaper-scraper",
        "--session-file", str(cli_session_path),
        "--key-file", str(cli_key_path)
    ])
    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()
    
    called_kwargs = mock_auth.call_args[1]
    assert called_kwargs['session_file'] == cli_session_path
    assert called_kwargs['key_file'] == cli_key_path
    
    mock_auth.reset_mock()

    # Case 2: Files in working directory
    monkeypatch.setattr("sys.argv", ["instapaper-scraper"])
    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()
            
    called_kwargs = mock_auth.call_args[1]
    assert called_kwargs['session_file'] == Path(".instapaper_session")
    assert called_kwargs['key_file'] == Path(".session_key")
    
    mock_auth.reset_mock()
    
    # Case 3: Files in user config directory
    (tmp_path / ".instapaper_session").unlink()
    (tmp_path / ".session_key").unlink()
    
    with patch("instapaper_scraper.cli.load_config", return_value={}):
        with patch("builtins.input", return_value="0"):
            cli.main()
            
    called_kwargs = mock_auth.call_args[1]
    assert called_kwargs['session_file'] == (user_config_dir / ".instapaper_session")
    assert called_kwargs['key_file'] == (user_config_dir / ".session_key")
