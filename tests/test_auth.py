import pytest
import stat
import requests
import requests_mock
from unittest.mock import MagicMock
from urllib.parse import parse_qs

from instapaper_scraper.auth import InstapaperAuthenticator, get_encryption_key


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


def test_login_with_credentials_success(authenticator, session, monkeypatch):
    """Test successful login with username and password."""
    monkeypatch.setenv("INSTAPAPER_USERNAME", "testuser")
    monkeypatch.setenv("INSTAPAPER_PASSWORD", "testpass")

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
        assert history[0].method == "POST"
        
        # The body is form-encoded, not JSON
        post_data = parse_qs(history[0].text)
        assert post_data["username"] == ["testuser"]
        assert post_data["password"] == ["testpass"]
        assert post_data["keep_logged_in"] == ["yes"]


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


def test_login_with_credentials_failure(authenticator, session, monkeypatch):
    """Test failed login with incorrect credentials."""
    monkeypatch.setenv("INSTAPAPER_USERNAME", "testuser")
    monkeypatch.setenv("INSTAPAPER_PASSWORD", "wrongpass")

    with requests_mock.Mocker() as m:
        m.post(
            "https://www.instapaper.com/user/login",
            text="login failed",
            status_code=200,
        )

        assert authenticator._login_with_credentials() is False


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
