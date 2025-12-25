import os
import getpass
import logging
import stat
from pathlib import Path
from typing import Union, Optional

from cryptography.fernet import Fernet
import requests

from .constants import INSTAPAPER_BASE_URL


# --- Encryption Helper ---
def get_encryption_key(key_file: Union[str, Path]) -> bytes:
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
    INSTAPAPER_VERIFY_URL = f"{INSTAPAPER_BASE_URL}/u"
    INSTAPAPER_LOGIN_URL = f"{INSTAPAPER_BASE_URL}/user/login"

    # Session/Cookie related
    COOKIE_PART_COUNT = 3
    REQUIRED_COOKIES = {"pfu", "pfp", "pfh"}
    LOGIN_FORM_IDENTIFIER = "login_form"
    LOGIN_SUCCESS_PATH = "/u"

    # Request related
    REQUEST_TIMEOUT = 10

    # Prompts
    PROMPT_USERNAME = "Enter your Instapaper username: "
    PROMPT_PASSWORD = "Enter your Instapaper password: "

    # Log messages
    LOG_NO_VALID_SESSION = "No valid session found. Please log in."
    LOG_LOGIN_SUCCESS = "Login successful."
    LOG_LOGIN_FAILED = "Login failed. Please check your credentials."
    LOG_SESSION_LOAD_SUCCESS = "Successfully logged in using the loaded session data."
    LOG_SESSION_LOAD_FAILED = "Session loaded but verification failed."
    LOG_SESSION_LOAD_ERROR = "Could not load session from {session_file}: {e}. A new session will be created."
    LOG_SESSION_VERIFY_FAILED = "Session verification request failed: {e}"
    LOG_NO_KNOWN_COOKIE_TO_SAVE = "Could not find a known session cookie to save."
    LOG_SAVED_SESSION = "Saved encrypted session to {session_file}."

    def __init__(
        self,
        session: requests.Session,
        session_file: Union[str, Path],
        key_file: Union[str, Path],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.session = session
        self.session_file = Path(session_file)
        self.key_file = Path(key_file)
        self.key = get_encryption_key(key_file)
        self.fernet = Fernet(self.key)
        self.username = username
        self.password = password

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
        """Checks if the current session is valid by making a request."""
        try:
            verify_response = self.session.get(
                self.INSTAPAPER_VERIFY_URL,
                timeout=self.REQUEST_TIMEOUT,
            )
            verify_response.raise_for_status()
            return self.LOGIN_FORM_IDENTIFIER not in verify_response.text
        except requests.RequestException as e:
            logging.error(self.LOG_SESSION_VERIFY_FAILED.format(e=e))
            return False

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

        login_response = self.session.post(
            self.INSTAPAPER_LOGIN_URL,
            data={"username": username, "password": password, "keep_logged_in": "yes"},
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
