# Shared constants used across the instapaper-scraper project.
from pathlib import Path

# --- General ---
APP_NAME = "instapaper-scraper"

# --- URLs ---
INSTAPAPER_BASE_URL = "https://www.instapaper.com"
INSTAPAPER_USER_SESSION_URL = f"{INSTAPAPER_BASE_URL}/data/user_session"
INSTAPAPER_BOOKMARKS_URL = f"{INSTAPAPER_BASE_URL}/data/bookmarks"

# Used by output.py to construct Instapaper read URLs.
INSTAPAPER_READ_URL = f"{INSTAPAPER_BASE_URL}/read/"

# --- Paths ---
CONFIG_DIR = Path.home() / ".config" / APP_NAME

# --- Article Data Keys ---
KEY_ID = "id"
KEY_TITLE = "title"
KEY_URL = "url"
KEY_ARTICLE_PREVIEW = "article_preview"

# Additional article fields available from the JSON API
# These are passed through in the article dict but are optional for output.
KEY_AUTHOR = "author"
KEY_DESCRIPTION = "description"  # maps to article_preview in output
KEY_TIME = "time"
KEY_SITE_NAME = "site_name"
KEY_TAGS = "tags"
KEY_NOTES = "notes"
KEY_LIKED = "liked"
KEY_IS_ARCHIVED = "is_archived"

# --- Section Types ---
SECTION_HOME = "home"
SECTION_LIKED = "liked"
SECTION_ARCHIVE = "archive"
SECTION_FOLDER = "folder"

SPECIAL_SECTIONS = {
    "liked": SECTION_LIKED,
    "archive": SECTION_ARCHIVE,
}

# --- Sort Options ---
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"

# --- Output Formats ---
SUPPORTED_FORMATS = ["csv", "json", "sqlite"]
