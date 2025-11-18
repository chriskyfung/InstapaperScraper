import importlib.metadata

try:
    __version__ = importlib.metadata.version("instapaper-scraper")
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    __version__ = "unknown"
