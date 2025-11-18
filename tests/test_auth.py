import pytest
import stat
import requests
import requests_mock
import logging
from unittest.mock import MagicMock
from urllib.parse import parse_qs
from pathlib import Path

from instapaper_scraper.auth import (
    InstapaperAuthenticator,
    get_encryption_key,
    InstapaperConstants,
)


@pytest.fixture
def session():
    """Pytest fixture for a requests session."""
    return requests.Session()


@pytest.fixture
def key_file(tmp_path):
    """Fixture for a temporary key file path."""
    return tmp_path / ".test_key"


@pytest.fixture
def session_file(tmp_path):
    """Fixture for a temporary session file path."""
    return tmp_path / ".test_session"


@pytest.fixture
def authenticator(session, session_file, key_file):
    """Fixture for the InstapaperAuthenticator."""
    return InstapaperAuthenticator(
        session, session_file=str(session_file), key_file=str(key_file)
    )


def test_get_encryption_key_creates_file(key_file):
    """Test that a key file is created with correct permissions."""
    key = get_encryption_key(str(key_file))
    assert key_file.exists()

    file_mode = key_file.stat().st_mode
    assert (
        file_mode & (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        == stat.S_IRUSR | stat.S_IWUSR
    )

    key2 = get_encryption_key(str(key_file))
    assert key == key2


def test_login_with_passed_credentials_success(session, session_file, key_file):
    """Test successful login with credentials passed to the constructor."""
    authenticator = InstapaperAuthenticator(
        session,
        session_file=str(session_file),
        key_file=str(key_file),
        username="arguser",
        password="argpassword",
    )

    with requests_mock.Mocker() as m:
        m.post(
            "https://www.instapaper.com/user/login",
            text="login success",
            status_code=302,
            headers={"Location": "/u"},
        )
        m.get("https://www.instapaper.com/u", text="logged in page")
        # Add cookies that would be set on a successful login
        session.cookies.set("pfu", "test_pfu")
        session.cookies.set("pfp", "test_pfp")
        session.cookies.set("pfh", "test_pfh")

        assert authenticator._login_with_credentials() is True
        history = m.request_history
        assert len(history) == 2
        post_data = parse_qs(history[0].text)
        assert post_data["username"] == ["arguser"]
        assert post_data["password"] == ["argpassword"]


def test_save_and_load_session(authenticator, session_file, key_file):
    """Test that a session can be saved and then successfully loaded."""
    # 1. Simulate a logged-in session
    authenticator.session.cookies.set("pfu", "user123", domain=".instapaper.com")
    authenticator.session.cookies.set("pfp", "pass123", domain=".instapaper.com")
    authenticator.session.cookies.set("pfh", "hash123", domain=".instapaper.com")

    # 2. Save the session
    authenticator._save_session()
    assert session_file.exists()

    # 3. Create a new authenticator and load the session
    new_session = requests.Session()
    new_auth = InstapaperAuthenticator(
        new_session, session_file=str(session_file), key_file=str(key_file)
    )

    # Mock the verification request
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u", text="logged in page")
        assert new_auth._load_session() is True

    # Verify cookies were loaded
    assert new_session.cookies.get("pfu") == "user123"
    assert new_session.cookies.get("pfp") == "pass123"


def test_load_session_verification_fails(authenticator, session_file, key_file):
    """Test that loading a session fails if verification fails."""
    # Save a valid session first
    authenticator.session.cookies.set("pfu", "user123", domain=".instapaper.com")
    authenticator._save_session()

    # Now, create a new authenticator to load it
    new_session = requests.Session()
    new_auth = InstapaperAuthenticator(
        new_session, session_file=str(session_file), key_file=str(key_file)
    )

    # Mock the verification request to return the login form
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u", text='<div id="login_form"></div>')
        assert new_auth._load_session() is False

    # The invalid cookies should have been cleared
    assert len(new_session.cookies) == 0


def test_load_session_corrupted_file(authenticator, session_file, caplog):
    """Test that a corrupted session file is handled gracefully."""
    # Write garbage to the session file
    with open(session_file, "wb") as f:
        f.write(b"this is not encrypted data")

    assert authenticator._load_session() is False
    assert f"Could not load session from {session_file}" in caplog.text
    # The corrupted file should be deleted
    assert not session_file.exists()


def test_full_login_flow_loads_from_session(authenticator, monkeypatch):
    """Test the main `login` method when a valid session exists."""
    # Mock _load_session to return True
    monkeypatch.setattr(authenticator, "_load_session", lambda: True)
    mock_login_creds = MagicMock()
    monkeypatch.setattr(authenticator, "_login_with_credentials", mock_login_creds)

    assert authenticator.login() is True
    # _login_with_credentials should not have been called
    mock_login_creds.assert_not_called()


def test_full_login_flow_uses_credentials(authenticator, monkeypatch):
    """Test the main `login` method when no session exists."""
    # Mock _load_session to return False
    monkeypatch.setattr(authenticator, "_load_session", lambda: False)
    # Mock _login_with_credentials to succeed
    monkeypatch.setattr(authenticator, "_login_with_credentials", lambda: True)
    # Mock _save_session
    mock_save = MagicMock()
    monkeypatch.setattr(authenticator, "_save_session", mock_save)

    assert authenticator.login() is True
    mock_save.assert_called_once()


def test_authenticator_init_defaults(session, monkeypatch, tmp_path):
    """Test InstapaperAuthenticator uses default file paths if not provided."""
    # 1. Setup mock paths
    mock_config_dir = tmp_path / ".config" / "instapaper-scraper"
    expected_key_file = mock_config_dir / ".session_key"
    expected_session_file = mock_config_dir / ".instapaper_session"

    # 2. Monkeypatch the constants in the auth module to use the mock paths
    monkeypatch.setattr(InstapaperConstants, "CONFIG_DIR", mock_config_dir)
    monkeypatch.setattr(InstapaperConstants, "DEFAULT_KEY_FILE", expected_key_file)
    monkeypatch.setattr(
        InstapaperConstants, "DEFAULT_SESSION_FILE", expected_session_file
    )

    # 3. Mock get_encryption_key to prevent actual file creation and to check calls
    from cryptography.fernet import Fernet

    mock_get_encryption_key = MagicMock(return_value=Fernet.generate_key())
    monkeypatch.setattr(
        "instapaper_scraper.auth.get_encryption_key", mock_get_encryption_key
    )

    # 4. Instantiate the authenticator without providing file paths
    authenticator = InstapaperAuthenticator(session)

    # 5. Assert that the authenticator has the correct default paths
    assert authenticator.session_file == expected_session_file
    mock_get_encryption_key.assert_called_once_with(expected_key_file)


def test_login_with_credentials_interactive_input(authenticator, session, monkeypatch):
    """Test _login_with_credentials prompts for input when no env vars or args."""
    authenticator.username = None
    authenticator.password = None

    mock_input = MagicMock(side_effect=["interactive_user", "interactive_pass"])
    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr("getpass.getpass", mock_input)

    with requests_mock.Mocker() as m:
        m.post(
            "https://www.instapaper.com/user/login",
            text="login success",
            status_code=302,
            headers={"Location": "/u"},
        )
        m.get("https://www.instapaper.com/u", text="logged in page")
        session.cookies.set("pfu", "test_pfu")
        session.cookies.set("pfp", "test_pfp")
        session.cookies.set("pfh", "test_pfh")

        assert authenticator._login_with_credentials() is True
        assert mock_input.call_count == 2
        post_data = parse_qs(m.request_history[0].text)
        assert post_data["username"] == ["interactive_user"]
        assert post_data["password"] == ["interactive_pass"]


def test_verify_session_request_exception(authenticator, caplog):
    """Test _verify_session handles requests.RequestException."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u",
            exc=requests.exceptions.ConnectionError("Test connection error"),
        )

        with caplog.at_level(logging.ERROR):
            assert authenticator._verify_session() is False
            assert (
                "Session verification request failed: Test connection error"
                in caplog.text
            )


def test_save_session_no_known_cookies(authenticator, session_file, caplog):
    """Test _save_session when no required cookies are present."""
    authenticator.session.cookies.clear()  # Ensure no cookies are set

    with caplog.at_level(logging.WARNING):
        authenticator._save_session()
        assert "Could not find a known session cookie to save." in caplog.text
        assert not session_file.exists()  # File should not be created
