import logging
import stat
from unittest.mock import MagicMock
from urllib.parse import parse_qs

import pytest
import requests
import requests_mock

from instapaper_scraper.auth import (
    InstapaperAuthenticator,
    get_encryption_key,
)
from instapaper_scraper.constants import INSTAPAPER_USER_SESSION_URL


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
        # Model Instapaper setting the CSRF cookie on the login page GET.
        # (requests_mock does not persist Set-Cookie to the session, so we
        # pre-seed the cookie instead.)
        session.cookies.set("_xsrf", "test_xsrf")
        m.get(
            "https://www.instapaper.com/user/login",
            text="<form id='login_form'></form>",
        )
        m.post(
            "https://www.instapaper.com/user/login",
            text="login success",
            status_code=302,
            headers={"Location": "/home"},
        )
        m.get("https://www.instapaper.com/home", text="logged in page")
        # Add cookies that would be set on a successful login
        session.cookies.set("pfus", "test_pfus")
        session.cookies.set("pfps", "test_pfps")
        session.cookies.set("pfhs", "test_pfhs")

        assert authenticator._login_with_credentials() is True
        history = m.request_history
        # 1 preflight GET (for _xsrf) + 1 POST + 1 redirect follow to /home
        assert [r.method for r in history] == ["GET", "POST", "GET"]
        post_data = parse_qs(history[1].text)
        assert post_data["username"] == ["arguser"]
        assert post_data["password"] == ["argpassword"]
        assert post_data["_xsrf"] == ["test_xsrf"]


def test_save_and_load_session(authenticator, session_file, key_file):
    """Test that a session can be saved and then successfully loaded."""
    # 1. Simulate a logged-in session
    authenticator.session.cookies.set("pfus", "user123", domain=".instapaper.com")
    authenticator.session.cookies.set("pfps", "pass123", domain=".instapaper.com")
    authenticator.session.cookies.set("pfhs", "hash123", domain=".instapaper.com")

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
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            json={"user": {"username": "user123", "form_key": "key123"}},
        )
        assert new_auth._load_session() is True

    # The form_key captured during verification is exposed for the client
    assert new_auth.form_key == "key123"

    # Verify all required cookies were round-tripped through the file.
    # (Only REQUIRED_COOKIES — pfus, pfps, pfhs — are saved; _xsrf is
    # deliberately not persisted.)
    assert new_session.cookies.get("pfus") == "user123"
    assert new_session.cookies.get("pfps") == "pass123"
    assert new_session.cookies.get("pfhs") == "hash123"


def test_load_session_verification_fails(authenticator, session_file, key_file):
    """Test that loading a session fails if verification fails."""
    # Save a valid session first
    authenticator.session.cookies.set("pfus", "user123", domain=".instapaper.com")
    authenticator._save_session()

    # Now, create a new authenticator to load it
    new_session = requests.Session()
    new_auth = InstapaperAuthenticator(
        new_session, session_file=str(session_file), key_file=str(key_file)
    )

    # Mock the verification request to signal an unauthenticated session
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, status_code=403, text="Forbidden")
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


def test_login_with_credentials_interactive_input(authenticator, session, monkeypatch):
    """Test _login_with_credentials prompts for input when no env vars or args."""
    authenticator.username = None
    authenticator.password = None

    mock_input = MagicMock(side_effect=["interactive_user", "interactive_pass"])
    monkeypatch.setattr("builtins.input", mock_input)
    monkeypatch.setattr("getpass.getpass", mock_input)

    with requests_mock.Mocker() as m:
        session.cookies.set("_xsrf", "test_xsrf")
        m.get(
            "https://www.instapaper.com/user/login",
            text="<form id='login_form'></form>",
        )
        m.post(
            "https://www.instapaper.com/user/login",
            text="login success",
            status_code=302,
            headers={"Location": "/home"},
        )
        m.get("https://www.instapaper.com/home", text="logged in page")
        session.cookies.set("pfus", "test_pfus")
        session.cookies.set("pfps", "test_pfps")
        session.cookies.set("pfhs", "test_pfhs")

        assert authenticator._login_with_credentials() is True
        assert mock_input.call_count == 2
        post_data = parse_qs(m.request_history[1].text)
        assert post_data["username"] == ["interactive_user"]
        assert post_data["password"] == ["interactive_pass"]
        assert post_data["_xsrf"] == ["test_xsrf"]


def test_verify_session_request_exception(authenticator, caplog):
    """Test _verify_session handles requests.RequestException."""
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
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


def test_full_login_flow_fails(authenticator, monkeypatch):
    """Test the main `login` method when both loading and credential login fail."""
    monkeypatch.setattr(authenticator, "_load_session", lambda: False)
    monkeypatch.setattr(authenticator, "_login_with_credentials", lambda: False)
    mock_save = MagicMock()
    monkeypatch.setattr(authenticator, "_save_session", mock_save)

    assert authenticator.login() is False
    mock_save.assert_not_called()


def test_load_session_with_request_exception(authenticator, session_file, caplog):
    """Test _load_session returns False when _verify_session raises an exception."""
    # Save a valid session first
    authenticator.session.cookies.set("pfus", "user123", domain=".instapaper.com")
    authenticator._save_session()

    # Create a new authenticator
    new_session = requests.Session()
    new_auth = InstapaperAuthenticator(
        new_session,
        session_file=str(session_file),
        key_file=str(authenticator.key_file),
    )

    # Mock the verification request to raise an exception
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            exc=requests.exceptions.ConnectionError,
        )
        with caplog.at_level(logging.WARNING):
            assert new_auth._load_session() is False
            assert "Session loaded but verification failed." in caplog.text


def test_login_with_credentials_failure(authenticator, session, caplog):
    """Test the _login_with_credentials method when the login fails."""
    authenticator.username = "user"
    authenticator.password = "pass"
    with requests_mock.Mocker() as m:
        session.cookies.set("_xsrf", "test_xsrf")
        m.get(
            "https://www.instapaper.com/user/login",
            text="<form id='login_form'></form>",
        )
        m.post("https://www.instapaper.com/user/login", status_code=200)
        with caplog.at_level(logging.ERROR):
            assert authenticator._login_with_credentials() is False
            assert "Login failed. Please check your credentials." in caplog.text


def test_login_without_xsrf_cookie_still_posts(session, session_file, key_file):
    """If the preflight GET does not yield an _xsrf cookie, the POST is still
    attempted (without echoing _xsrf) — covers the falsy branch of the guard."""
    authenticator = InstapaperAuthenticator(
        session,
        session_file=str(session_file),
        key_file=str(key_file),
        username="arguser",
        password="argpassword",
    )

    with requests_mock.Mocker() as m:
        # No _xsrf pre-seeded on the session.
        m.get(
            "https://www.instapaper.com/user/login",
            text="<form id='login_form'></form>",
        )
        m.post(
            "https://www.instapaper.com/user/login",
            text="login success",
            status_code=302,
            headers={"Location": "/home"},
        )
        m.get("https://www.instapaper.com/home", text="logged in page")
        session.cookies.set("pfus", "test_pfus")
        session.cookies.set("pfps", "test_pfps")
        session.cookies.set("pfhs", "test_pfhs")

        assert authenticator._login_with_credentials() is True
        post_body = parse_qs(m.request_history[1].text)
        assert "_xsrf" not in post_body


def test_login_csrf_preflight_failure(authenticator, session, caplog):
    """Test _login_with_credentials returns False when the CSRF preflight GET fails."""
    authenticator.username = "user"
    authenticator.password = "pass"
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/user/login",
            exc=requests.exceptions.ConnectionError("boom"),
        )
        with caplog.at_level(logging.ERROR):
            assert authenticator._login_with_credentials() is False
            assert (
                "Could not fetch login page for CSRF token (network error)"
                in caplog.text
            )
        # POST must not fire if the preflight failed.
        assert all(r.method == "GET" for r in m.request_history)


def test_login_csrf_preflight_403(authenticator, session, caplog):
    """Test _login_with_credentials returns False when preflight GET returns 403."""
    authenticator.username = "user"
    authenticator.password = "pass"
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/user/login",
            status_code=403,
            text="Forbidden",
        )
        with caplog.at_level(logging.ERROR):
            assert authenticator._login_with_credentials() is False
            assert "server returned 403 Forbidden" in caplog.text
        # POST must not fire if the preflight got 403.
        assert all(r.method == "GET" for r in m.request_history)


def test_verify_session_success_captures_form_key(authenticator):
    """A valid /data/user_session response marks the session verified and
    captures the form_key from the same payload."""
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            json={"user": {"username": "me", "form_key": "abc123"}},
        )
        assert authenticator._verify_session() is True
        assert authenticator.form_key == "abc123"
        assert m.last_request.headers["x-requested-with"] == "XMLHttpRequest"


def test_verify_session_fails_without_user_object(authenticator):
    """A 200 response whose JSON lacks a user object is not a valid session."""
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, json={"error": "not logged in"})
        assert authenticator._verify_session() is False
        assert authenticator.form_key is None


def test_verify_session_fails_on_non_json(authenticator):
    """A 200 HTML response (e.g. a login page) fails verification."""
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, text="<html>login</html>")
        assert authenticator._verify_session() is False


def test_verify_session_fails_on_non_ok(authenticator, caplog):
    """A non-2xx response (e.g. 500) returns False and logs the status code."""
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, status_code=500, text="oops")
        with caplog.at_level(logging.ERROR):
            assert authenticator._verify_session() is False
            assert "returned status 500" in caplog.text


def test_load_session_skips_malformed_cookie_lines(authenticator, session_file, caplog):
    """Cookie lines without exactly name:value:domain are skipped, not
    silently parsed into corrupted values."""
    cookie_data = "pfus:user123:.instapaper.com\nbroken-line-no-colons\n"
    encrypted = authenticator.fernet.encrypt(cookie_data.encode("utf-8"))
    session_file.write_bytes(encrypted)

    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            json={"user": {"username": "user123", "form_key": "k"}},
        )
        with caplog.at_level(logging.WARNING):
            assert authenticator._load_session() is True
            assert "malformed cookie line" in caplog.text
    assert authenticator.session.cookies.get("pfus") == "user123"


def test_load_session_colon_in_cookie_value(session, session_file, key_file):
    """Documents a known limitation of the name:value:domain line format:
    a cookie value containing ':' is truncated at the first colon (the
    remainder is treated as the domain). Auth values (pfus/pfps/pfhs) are
    hex tokens in practice, so this does not occur for them; if a colon-
    bearing cookie ever mattered, the file format would need escaping."""
    authenticator = InstapaperAuthenticator(
        session, session_file=str(session_file), key_file=str(key_file)
    )
    authenticator.session.cookies.set("pfus", "a:b:c", domain=".instapaper.com")
    authenticator._save_session()

    new_session = requests.Session()
    new_auth = InstapaperAuthenticator(
        new_session, session_file=str(session_file), key_file=str(key_file)
    )
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            json={"user": {"username": "u", "form_key": "k"}},
        )
        assert new_auth._load_session() is True
    assert new_session.cookies.get("pfus") == "a"
