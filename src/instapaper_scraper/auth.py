import getpass
import logging
import os
import stat
from pathlib import Path

import requests
from cryptography.fernet import Fernet

from .constants import (
    INSTAPAPER_BASE_URL,
    INSTAPAPER_USER_SESSION_URL,
    XHR_HEADERS,
)


# --- Encryption Helper ---
def get_encryption_key(key_file: str | Path) -> bytes:
    """
    Loads the encryption key from a file or generates a new one.
    Sets strict file permissions for the key file.
    """
    key_path = Path(key_file)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        with open(key_path, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        # Set file permissions to 0600 (owner read/write only)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(f"Generated new encryption key at {key_path}.")
    return key


class InstapaperAuthenticator:
    # URLs
    # NOTE: /u is no longer usable for session verification because it now
    # returns 200 regardless of login state. /data/user_session returns a
    # JSON payload with a "user" object only for authenticated sessions.
    INSTAPAPER_VERIFY_URL = INSTAPAPER_USER_SESSION_URL
    INSTAPAPER_LOGIN_URL = f"{INSTAPAPER_BASE_URL}/user/login"

    # Headers for the verification request, mirroring the web app's XHR.
    # Shared with api.py so both callers of /data/user_session match.
    VERIFY_HEADERS = XHR_HEADERS

    # Session/Cookie related
    COOKIE_PART_COUNT = 3
    REQUIRED_COOKIES = {"pfus", "pfps", "pfhs"}
    LOGIN_SUCCESS_PATH = "/home"
    XSRF_COOKIE_NAME = "_xsrf"

    # Request related
    REQUEST_TIMEOUT = 10

    # Prompts
    PROMPT_USERNAME = "Enter your Instapaper username: "
    PROMPT_PASSWORD = "Enter your Instapaper password: "

    # Log messages
    LOG_NO_VALID_SESSION = "No valid session found. Please log in."
    LOG_LOGIN_SUCCESS = "Login successful."
    LOG_LOGIN_FAILED = "Login failed. Please check your credentials."
    LOG_CSRF_FETCH_NETWORK_FAILED = (
        "Could not fetch login page for CSRF token (network error): {e}"
    )
    LOG_CSRF_FETCH_FORBIDDEN = (
        "Could not fetch login page for CSRF token: server returned 403 Forbidden."
    )
    LOG_SESSION_VERIFY_NON_OK = (
        "Session verification failed: /data/user_session returned status {status_code}."
    )
    LOG_SESSION_VERIFY_NOT_JSON = (
        "Session verification failed: /data/user_session did not return JSON."
    )
    LOG_SESSION_VERIFY_NO_USER = (
        "Session verification failed: no user object in /data/user_session response."
    )
    LOG_MALFORMED_COOKIE_LINE = (
        "Skipping malformed cookie line in session file (expected name:value:domain)."
    )
    LOG_SESSION_LOAD_SUCCESS = "Successfully logged in using the loaded session data."
    LOG_SESSION_LOAD_FAILED = "Session loaded but verification failed."
    LOG_SESSION_LOAD_ERROR = "Could not load session from {session_file}: {e}. A new session will be created."
    LOG_SESSION_VERIFY_FAILED = "Session verification request failed: {e}"
    LOG_SESSION_NO_FORM_KEY = (
        "form_key not present in user_session payload; "
        "client will fetch it on first use."
    )
    LOG_NO_KNOWN_COOKIE_TO_SAVE = "Could not find a known session cookie to save."
    LOG_SAVED_SESSION = "Saved encrypted session to {session_file}."

    def __init__(
        self,
        session: requests.Session,
        session_file: str | Path,
        key_file: str | Path,
        username: str | None = None,
        password: str | None = None,
    ):
        self.session = session
        self.session_file = Path(session_file)
        self.key_file = Path(key_file)
        self.key = get_encryption_key(key_file)
        self.fernet = Fernet(self.key)
        self.username = username
        self.password = password
        # Captured from /data/user_session during verification; handed to
        # the API client so it does not need to re-fetch it.
        self.form_key: str | None = None

    def login(self) -> bool:
        """
        Handles the complete login process:
        1. Tries to load an existing session.
        2. If that fails, prompts for credentials and logs in.
        3. Saves the new session.
        """
        if self._load_session():
            return True

        if self._login_with_credentials():
            self._save_session()
            return True

        return False

    def _load_session(self) -> bool:
        """Tries to load and verify a session from the session file."""
        if not self.session_file.exists():
            return False

        logging.info(f"Loading encrypted session from {self.session_file}...")
        try:
            with open(self.session_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.fernet.decrypt(encrypted_data).decode("utf-8")

            for line in decrypted_data.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":", 2)
                if len(parts) == self.COOKIE_PART_COUNT:
                    name, value, domain = parts
                    self.session.cookies.set(name, value, domain=domain)
                else:
                    logging.warning(self.LOG_MALFORMED_COOKIE_LINE)

            if self.session.cookies and self._verify_session():
                logging.info(self.LOG_SESSION_LOAD_SUCCESS)
                return True
            else:
                logging.warning(self.LOG_SESSION_LOAD_FAILED)
                # Clear cookies if verification fails
                self.session.cookies.clear()
                return False

        except Exception as e:
            logging.warning(
                self.LOG_SESSION_LOAD_ERROR.format(session_file=self.session_file, e=e)
            )
            self.session_file.unlink(missing_ok=True)
            return False

    def _verify_session(self) -> bool:
        """Checks if the current session is valid via /data/user_session.

        The previous check (GET /u, asserting "login_form" was absent) no
        longer works because /u returns 200 regardless of login state.
        /data/user_session returns a JSON payload containing a "user" object
        only for authenticated sessions, so it is a reliable probe. As a
        side effect, the form_key issued in the same payload is captured so
        it can be handed to the API client without a second request.
        """
        self.form_key = None
        try:
            # Network errors only — response parsing is handled below.
            verify_response = self.session.get(
                self.INSTAPAPER_VERIFY_URL,
                headers=self.VERIFY_HEADERS,
                timeout=self.REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            logging.error(self.LOG_SESSION_VERIFY_FAILED.format(e=e))
            return False

        if not verify_response.ok:
            logging.error(
                self.LOG_SESSION_VERIFY_NON_OK.format(
                    status_code=verify_response.status_code
                )
            )
            return False

        try:
            data = verify_response.json()
        except ValueError:
            logging.error(self.LOG_SESSION_VERIFY_NOT_JSON)
            return False

        user = data.get("user") if isinstance(data, dict) else None
        if not isinstance(user, dict):
            logging.error(self.LOG_SESSION_VERIFY_NO_USER)
            return False

        self.form_key = user.get("form_key")
        if not self.form_key:
            logging.debug(self.LOG_SESSION_NO_FORM_KEY)
        return True

    def _fetch_csrf_token(self) -> tuple[bool, str | None]:
        """Fetches the CSRF token via a preflight GET to the login page.

        Returns:
            A tuple of (success, token). On success the token may still be None
            if the server did not set the cookie.
        """
        try:
            response = self.session.get(
                self.INSTAPAPER_LOGIN_URL, timeout=self.REQUEST_TIMEOUT
            )
        except requests.RequestException as e:
            logging.error(self.LOG_CSRF_FETCH_NETWORK_FAILED.format(e=e))
            return False, None

        if response.status_code == 403:
            logging.error(self.LOG_CSRF_FETCH_FORBIDDEN)
            return False, None

        token = self.session.cookies.get(self.XSRF_COOKIE_NAME)
        return True, token

    def _login_with_credentials(self) -> bool:
        """Logs in using username/password from arguments or user prompt."""
        logging.info(self.LOG_NO_VALID_SESSION)
        username = self.username
        password = self.password

        if not username or not password:
            username = input(self.PROMPT_USERNAME)
            password = getpass.getpass(self.PROMPT_PASSWORD)
        elif self.username:
            logging.info(
                f"Using username '{self.username}' from command-line arguments."
            )

        # Preflight GET to obtain the _xsrf cookie Instapaper now requires
        # on the login POST body; without it the server returns 403.
        ok, xsrf = self._fetch_csrf_token()
        if not ok:
            return False

        login_payload = {
            "username": username,
            "password": password,
            "keep_logged_in": "yes",
        }
        if xsrf:
            login_payload[self.XSRF_COOKIE_NAME] = xsrf

        login_response = self.session.post(
            self.INSTAPAPER_LOGIN_URL,
            data=login_payload,
            timeout=self.REQUEST_TIMEOUT,
        )

        required_cookies = self.REQUIRED_COOKIES
        found_cookies = {c.name for c in self.session.cookies}

        if self.LOGIN_SUCCESS_PATH in login_response.url and required_cookies.issubset(
            found_cookies
        ):
            logging.info(self.LOG_LOGIN_SUCCESS)
            return True
        else:
            logging.error(self.LOG_LOGIN_FAILED)
            return False

    def _save_session(self) -> None:
        """Saves the current session cookies to an encrypted file."""
        required_cookies = self.REQUIRED_COOKIES
        cookies_to_save = [
            c for c in self.session.cookies if c.name in required_cookies
        ]

        if not cookies_to_save:
            logging.warning(self.LOG_NO_KNOWN_COOKIE_TO_SAVE)
            return

        cookie_data = ""
        for cookie in cookies_to_save:
            cookie_data += f"{cookie.name}:{cookie.value}:{cookie.domain}\n"

        encrypted_data = self.fernet.encrypt(cookie_data.encode("utf-8"))

        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "wb") as f:
            f.write(encrypted_data)

        os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(self.LOG_SAVED_SESSION.format(session_file=self.session_file))
