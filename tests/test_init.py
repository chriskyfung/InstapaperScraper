import importlib
import importlib.metadata

import instapaper_scraper


def test_version_found(monkeypatch):
    """Test that __version__ is correctly read when the package is installed."""
    # Mock importlib.metadata.version to return a specific version
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.0.0")

    # We need to reload the module to re-execute the __init__.py code
    importlib.reload(instapaper_scraper)

    assert instapaper_scraper.__version__ == "1.0.0"


def test_version_not_found(monkeypatch):
    """Test that __version__ is 'unknown' when the package is not found."""

    # Mock importlib.metadata.version to raise PackageNotFoundError
    def mock_version_not_found(name):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", mock_version_not_found)

    # Reload the module to re-execute the __init__.py code
    importlib.reload(instapaper_scraper)

    assert instapaper_scraper.__version__ == "unknown"
