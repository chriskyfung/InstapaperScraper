# Shared constants used across the instapaper-scraper project.
from pathlib import Path

# --- General ---
APP_NAME = "instapaper-scraper"

# --- URLS ---
INSTAPAPER_BASE_URL = "https://www.instapaper.com"
INSTAPAPER_READ_URL = f"{INSTAPAPER_BASE_URL}/read/"

# --- Paths ---
CONFIG_DIR = Path.home() / ".config" / APP_NAME

# --- Article Data Keys ---
KEY_ID = "id"
KEY_TITLE = "title"
KEY_URL = "url"
