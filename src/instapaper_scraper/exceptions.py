class InstapaperAPIError(Exception):
    """Raised when the Instapaper JSON API returns an error response."""

    pass


class ApiResponseError(InstapaperAPIError):
    """Raised when the Instapaper JSON API returns an unexpected response."""

    pass
