class InstapaperAPIError(Exception):
    """Raised when the Instapaper JSON API returns an error response."""

    pass


class ApiResponseError(InstapaperAPIError):
    """Raised when the Instapaper JSON API returns an unexpected response."""

    pass


class ApiParseError(ApiResponseError):
    """Raised when the Instapaper JSON API response cannot be parsed."""

    pass


class ApiNetworkError(ApiResponseError):
    """Raised when a network error occurs while contacting the Instapaper API."""

    pass
