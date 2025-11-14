import os
import getpass
import logging
import stat
from cryptography.fernet import Fernet
import requests


# --- Encryption Helper ---
def get_encryption_key(key_file: str = ".session_key") -> bytes:
    """
    Loads the encryption key from a file or generates a new one.
    Sets strict file permissions for the key file.
    """
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        # Set file permissions to 0600 (owner read/write only)
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(f"Generated new encryption key at {key_file}.")
    return key


class InstapaperAuthenticator:
    def __init__(
        self,
        session: requests.Session,
        session_file: str = ".instapaper_session",
        key_file: str = ".session_key",
    ):
        self.session = session
        self.session_file = session_file
        self.key = get_encryption_key(key_file)
        self.fernet = Fernet(self.key)

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
        if not os.path.exists(self.session_file):
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
                if len(parts) == 3:
                    name, value, domain = parts
                    self.session.cookies.set(name, value, domain=domain)

            if self.session.cookies and self._verify_session():
                logging.info("Successfully logged in using the loaded session data.")
                return True
            else:
                logging.warning("Session loaded but verification failed.")
                # Clear cookies if verification fails
                self.session.cookies.clear()
                return False

        except Exception as e:
            logging.warning(
                f"Could not load session from {self.session_file}: {e}. A new session will be created."
            )
            os.remove(self.session_file)
            return False

    def _verify_session(self) -> bool:
        """Checks if the current session is valid by making a request."""
        try:
            verify_response = self.session.get(
                "https://www.instapaper.com/u", timeout=10
            )
            verify_response.raise_for_status()
            return "login_form" not in verify_response.text
        except requests.RequestException as e:
            logging.error(f"Session verification request failed: {e}")
            return False

    def _login_with_credentials(self) -> bool:
        """Logs in using username/password from .env or user prompt."""
        logging.info("No valid session found. Please log in.")
        username = os.getenv("INSTAPAPER_USERNAME")
        password = os.getenv("INSTAPAPER_PASSWORD")

        if username and password:
            logging.info(f"Using username '{username}' from environment variables.")
        else:
            username = input("Enter your Instapaper username: ")
            password = getpass.getpass("Enter your Instapaper password: ")

        login_response = self.session.post(
            "https://www.instapaper.com/user/login",
            data={"username": username, "password": password, "keep_logged_in": "yes"},
            timeout=10,
        )

        required_cookies = {"pfu", "pfp", "pfh"}
        found_cookies = {c.name for c in self.session.cookies}

        if "/u" in login_response.url and required_cookies.issubset(found_cookies):
            logging.info("Login successful.")
            return True
        else:
            logging.error("Login failed. Please check your credentials.")
            return False

    def _save_session(self):
        """Saves the current session cookies to an encrypted file."""
        required_cookies = ["pfu", "pfp", "pfh"]
        cookies_to_save = [
            c for c in self.session.cookies if c.name in required_cookies
        ]

        if not cookies_to_save:
            logging.warning("Could not find a known session cookie to save.")
            return

        cookie_data = ""
        for cookie in cookies_to_save:
            cookie_data += f"{cookie.name}:{cookie.value}:{cookie.domain}\n"

        encrypted_data = self.fernet.encrypt(cookie_data.encode("utf-8"))

        with open(self.session_file, "wb") as f:
            f.write(encrypted_data)

        os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(f"Saved encrypted session to {self.session_file}.")
