class InstapaperAPIError(Exception):
    """Raised when the Instapaper JSON API returns an error response."""


class SessionLogoutError(OSError):
    """Raised when a stored session file (or key file) cannot be deleted.

    Distinct from the idempotent no-op case where no session exists, so
    callers can tell a genuine filesystem failure apart from a harmless
    "nothing to remove" outcome.
    """


class ApiResponseError(InstapaperAPIError):
    """Raised when the Instapaper JSON API returns an unexpected response."""


class ApiParseError(ApiResponseError):
    """Raised when the Instapaper JSON API response cannot be parsed."""


class ApiNetworkError(ApiResponseError):
    """Raised when a network error occurs while contacting the Instapaper API."""
