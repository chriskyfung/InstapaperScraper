import getpass
import json
import logging
import os
import stat
from http.cookiejar import Cookie
from pathlib import Path
from typing import Any, cast

import requests
from cryptography.fernet import Fernet

from .constants import (
    INSTAPAPER_BASE_URL,
    INSTAPAPER_USER_SESSION_URL,
    XHR_HEADERS,
)


# --- Log Redaction Helper ---
def _mask_cookie_header(header: str) -> str:
    """Masks cookie values in a Cookie header for safe logging.

    Values longer than 8 characters become name=abcd...wxyz; shorter ones
    are fully redacted. Tokens without an '=' separator are kept as-is.
    """
    parts = []
    for pair in header.split("; "):
        name, separator, value = pair.partition("=")
        if not separator:
            parts.append(name)
        elif len(value) <= 8:
            parts.append(f"{name}=<redacted>")
        else:
            parts.append(f"{name}={value[:4]}...{value[-4:]}")
    return "; ".join(parts)


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
    INSTAPAPER_LOGIN_URL = f"{INSTAPAPER_BASE_URL}/user/login"

    # Session/Cookie related
    COOKIE_PART_COUNT = 3
    # Storage format v2: a JSON payload (robust against special characters
    # in cookie values). v1 was the legacy "name:value:domain" line format.
    SESSION_FORMAT_VERSION = 2
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
    LOG_LEGACY_SESSION_FORMAT = (
        "Session file uses the legacy line format; it will be upgraded "
        "to JSON on the next save."
    )
    LOG_SAVE_VERIFY_FAILED = (
        "Post-save self-check failed: the session file does not read back "
        "identically. The stored session may be corrupted."
    )
    LOG_SESSION_LOAD_SUCCESS = "Successfully logged in using the loaded session data."
    LOG_SESSION_LOAD_FAILED = "Session loaded but verification failed."
    LOG_SESSION_LOAD_ERROR = "Could not load session from {session_file}: {e}. A new session will be created."
    LOG_SESSION_VERIFY_FAILED = "Session verification request failed: {e}"
    LOG_SESSION_RETRY_MINIMAL = (
        "Retrying session verification with minimal cookie set "
        "(pfus/pfps/pfhs only), mirroring the browser request."
    )
    LOG_SESSION_MINIMAL_OK = (
        "Session verified with minimal cookie set; the full cookie jar "
        "(e.g. a stale _xsrf) may be interfering with /data endpoints."
    )
    LOG_SESSION_MINIMAL_NO_COOKIES = (
        "Cannot retry verification: none of the required auth cookies "
        "(pfus/pfps/pfhs) are present."
    )
    LOG_VERIFY_DEBUG = (
        "Verification attempt: url=%s status=%s content_type=%s "
        "body_bytes=%s cookies_sent=%s"
    )
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
            cookies = self._parse_session_payload(decrypted_data)

            for cookie in cookies:
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie["domain"],
                    path=cookie.get("path", "/"),
                    secure=cookie.get("secure", False),
                )

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

    def _parse_session_payload(self, decrypted_data: str) -> list[dict[str, Any]]:
        """Parses a decrypted session payload into cookie dicts.

        Supports the v2 JSON format and falls back to the v1 legacy
        "name:value:domain" line format for backward compatibility.
        """
        try:
            payload = json.loads(decrypted_data)
        except ValueError:
            payload = None

        if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
            return [
                cookie
                for cookie in payload["cookies"]
                if isinstance(cookie, dict) and "name" in cookie and "value" in cookie
            ]

        # Legacy v1 line format.
        logging.info(self.LOG_LEGACY_SESSION_FORMAT)
        cookies: list[dict[str, Any]] = []
        for line in decrypted_data.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) == self.COOKIE_PART_COUNT:
                name, value, domain = parts
                cookies.append({"name": name, "value": value, "domain": domain})
            else:
                logging.warning(self.LOG_MALFORMED_COOKIE_LINE)
        return cookies

    def _verify_session(self) -> bool:
        """Checks if the current session is valid via /data/user_session.

        (/u is unusable for verification: it returns 200 regardless of
        login state, so its old "login_form"-absence check never fired.)
        /data/user_session returns a JSON payload containing a "user" object
        only for authenticated sessions, so it is a reliable probe.

        Two attempts are made:
        1. A normal session request (full cookie jar, XHR headers).
        2. If the first attempt fails in any way (non-OK status, non-JSON
           body, or a payload without a user object), a retry that
           replicates the proven-working minimal request exactly: an
           explicit Cookie header containing only pfus/pfps/pfhs plus
           x-requested-with. This rules out interference from other
           restored cookies (e.g. a stale _xsrf) and from jar/cookie-policy
           quirks, which can manifest as any of those failure modes.

        As a side effect, the form_key issued in the payload is captured so
        it can be handed to the API client without a second request.
        """
        self.form_key = None

        response = self._user_session_request()
        if response is not None and self._parse_verification(response):
            return True

        if response is not None:
            # Any first-attempt failure (not just non-OK) triggers the
            # fallback: jar interference can produce a 200 response that
            # is HTML or lacks a user object, not only a rejection.
            logging.warning(self.LOG_SESSION_RETRY_MINIMAL)
            minimal_response = self._minimal_user_session_request()
            if minimal_response is not None:
                if self._parse_verification(minimal_response):
                    logging.info(self.LOG_SESSION_MINIMAL_OK)
                    return True
        return False

    def _user_session_request(self) -> requests.Response | None:
        """Normal verification request using the session's cookie jar."""
        try:
            # Network errors only — response parsing is handled by the caller.
            response = self.session.get(
                INSTAPAPER_USER_SESSION_URL,
                headers=XHR_HEADERS,
                timeout=self.REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            logging.error(self.LOG_SESSION_VERIFY_FAILED.format(e=e))
            return None
        self._log_verification_attempt(response)
        return response

    def _minimal_user_session_request(self) -> requests.Response | None:
        """Fallback verification request with only the pf* auth cookies.

        Replicates the known-good curl exactly: an explicit Cookie header
        (which requests preserves as-is) with just pfus/pfps/pfhs. A bare
        PreparedRequest is sent via the session's adapter so the cookie jar
        cannot merge any other cookies into the header.
        """
        cookie_header = self._minimal_cookie_header()
        if not cookie_header:
            logging.error(self.LOG_SESSION_MINIMAL_NO_COOKIES)
            return None

        headers = dict(XHR_HEADERS)
        headers["Cookie"] = cookie_header
        try:
            request = requests.Request(
                "GET", INSTAPAPER_USER_SESSION_URL, headers=headers
            ).prepare()
            response = self.session.send(request, timeout=self.REQUEST_TIMEOUT)
        except requests.RequestException as e:
            logging.error(self.LOG_SESSION_VERIFY_FAILED.format(e=e))
            return None
        self._log_verification_attempt(response)
        return response

    def _minimal_cookie_header(self) -> str | None:
        """Builds a Cookie header from only the required auth cookies."""
        # Read the Cookie objects directly: RequestsCookieJar.get()
        # normalizes an empty cookie value to None, so a get()-based
        # lookup cannot distinguish a missing cookie from an empty one.
        values: dict[str, str] = {}
        jar = cast("list[Cookie]", list(self.session.cookies))
        for cookie in jar:
            if cookie.name in self.REQUIRED_COOKIES:
                # Presence, not truthiness: an existing cookie with an
                # empty value must still be sent (the server may key on
                # its presence).
                values[cookie.name] = cookie.value if cookie.value is not None else ""
        if not values:
            return None
        return "; ".join(f"{name}={values[name]}" for name in sorted(values))

    def _log_verification_attempt(self, response: requests.Response) -> None:
        """Logs request/response details of a verification attempt.

        Cookie values are masked and the response body is never logged:
        both contain credential material (session cookies and the
        form_key) that must not leak into logs or support bundles.
        """
        cookie_header = response.request.headers.get("Cookie")
        masked_cookies = (
            _mask_cookie_header(cookie_header) if cookie_header else "<none>"
        )
        logging.debug(
            self.LOG_VERIFY_DEBUG,
            response.request.url,
            response.status_code,
            response.headers.get("content-type"),
            len(response.content),
            masked_cookies,
        )

    def _parse_verification(self, response: requests.Response) -> bool:
        """Interprets a /data/user_session response for session validity."""
        if not response.ok:
            logging.error(
                self.LOG_SESSION_VERIFY_NON_OK.format(status_code=response.status_code)
            )
            return False

        try:
            data = response.json()
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
        """Saves the current session cookies to an encrypted file.

        All cookies are persisted (not just the pf* auth cookies): the file
        is already Fernet-encrypted with owner-only permissions, and cookies
        such as _xsrf may be required for the restored session to behave
        like the original browser context. The v2 JSON payload is immune to
        special characters in cookie values. The write is fsynced and then
        verified by re-reading and decrypting the file from disk.
        """
        # Iterating a RequestsCookieJar yields Cookie objects at runtime,
        # but its type stubs declare Iterator[str]; cast for mypy.
        jar_cookies = cast("list[Cookie]", list(self.session.cookies))

        if not jar_cookies:
            logging.warning(self.LOG_NO_KNOWN_COOKIE_TO_SAVE)
            return

        cookies_payload = [
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": bool(cookie.secure),
            }
            for cookie in jar_cookies
        ]
        payload = json.dumps(
            {"version": self.SESSION_FORMAT_VERSION, "cookies": cookies_payload}
        )
        encrypted_data = self.fernet.encrypt(payload.encode("utf-8"))

        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "wb") as f:
            f.write(encrypted_data)
            # Force the write to stable storage so the disk re-read check
            # below actually validates the persisted bytes.
            f.flush()
            os.fsync(f.fileno())

        os.chmod(self.session_file, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(self.LOG_SAVED_SESSION.format(session_file=self.session_file))
        self._verify_saved_session(cookies_payload)

    def _verify_saved_session(self, cookies_payload: list[dict[str, Any]]) -> None:
        """Disk round-trip self-check: re-read the file just written from
        disk, decrypt it, and compare it with what was intended. Reading
        from disk (rather than the in-memory bytes) also catches partial
        writes and disk errors."""
        try:
            encrypted_on_disk = self.session_file.read_bytes()
            decrypted = self.fernet.decrypt(encrypted_on_disk).decode("utf-8")
            read_back = self._parse_session_payload(decrypted)

            def key(cookie: dict[str, Any]) -> tuple[str, str, str]:
                return (
                    cookie["name"],
                    cookie.get("domain", ""),
                    cookie.get("path", "/"),
                )

            # Compare full dicts: value, domain, path and secure must all
            # round-trip exactly for the stored session to be trustworthy.
            if sorted(cookies_payload, key=key) != sorted(read_back, key=key):
                logging.warning(self.LOG_SAVE_VERIFY_FAILED)
        except Exception as e:
            logging.warning(
                "Post-save self-check could not run: %s. The stored session "
                "may be corrupted.",
                e,
            )

    def dump_session(self) -> list[str]:
        """Returns masked one-line summaries of the stored session cookies.

        Values are masked (first4...last4) so the output can be compared
        against browser DevTools without exposing secrets.
        """
        if not self.session_file.exists():
            return [f"<no session file at {self.session_file}>"]
        try:
            with open(self.session_file, "rb") as f:
                encrypted_data = f.read()
            decrypted = self.fernet.decrypt(encrypted_data).decode("utf-8")
            cookies = self._parse_session_payload(decrypted)
        except Exception as e:
            return [f"<could not read session file ({type(e).__name__}): {e}>"]
        if not cookies:
            return ["<session file contains no cookies>"]
        return [
            f"{cookie['name']}={self._mask(cookie['value'])} ({cookie['domain']})"
            for cookie in cookies
        ]

    @staticmethod
    def _mask(value: str) -> str:
        if len(value) <= 8:
            return value
        return f"{value[:4]}...{value[-4:]}"
