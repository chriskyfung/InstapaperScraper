class InstapaperAPIError(Exception):
    """Raised when the Instapaper JSON API returns an error response."""


class ApiResponseError(InstapaperAPIError):
    """Raised when the Instapaper JSON API returns an unexpected response."""


class ApiParseError(ApiResponseError):
    """Raised when the Instapaper JSON API response cannot be parsed."""


class ApiNetworkError(ApiResponseError):
    """Raised when a network error occurs while contacting the Instapaper API."""
