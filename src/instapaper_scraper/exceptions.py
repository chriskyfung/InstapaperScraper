class InstapaperAPIError(Exception):
    """Raised when the Instapaper JSON API returns an error response."""

    pass


class ScraperStructureChanged(InstapaperAPIError):
    """Custom exception for when the scraper detects an HTML structure change.

    Kept for backward compatibility. New code should use InstapaperAPIError instead.
    """

    pass
