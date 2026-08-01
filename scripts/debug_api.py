"""Debug helper for InstapaperClient.

Run via the 'Debug API' VS Code launch configuration to set breakpoints in
api.py and step through the InstapaperClient methods (e.g. _fetch_form_key,
get_articles, _parse_bookmarks, _wait_for_retry, etc.).

This script uses requests_mock (a dev dependency) to mock the Instapaper API
responses, so no real credentials or network calls are required.

To debug a specific method:
  1. Set a breakpoint in src/instapaper_scraper/api.py.
  2. Select "Debug API" from the VS Code Run panel and press F5.
  3. Step through the mocked call flow.
"""

import requests
import requests_mock

from instapaper_scraper.api import InstapaperClient
from instapaper_scraper.constants import (
    INSTAPAPER_BOOKMARKS_URL,
    INSTAPAPER_USER_SESSION_URL,
)


def main() -> None:
    """Entry point for debugging the InstapaperClient API."""
    session = requests.Session()
    client = InstapaperClient(session)

    print("=== InstapaperClient Debug Helper ===")
    print(f"  max_retries:    {client.max_retries}")
    print(f"  backoff_factor: {client.backoff_factor}")
    print(f"  form_key:       {client._form_key}")
    print()

    # ---- Mock API responses ----
    mock_session_response = {
        "user": {
            "id": 12345,
            "email": "test@example.com",
            "username": "testuser",
            "form_key": "debug_form_key_1234567890",
            "folders": [],
            "tags": [],
        }
    }

    mock_bookmarks_response = {
        "bookmarks": [
            {
                "id": 1,
                "url": "https://example.com/1",
                "title": "Debug Article 1",
                "description": "A preview of article 1.",
                "author": "Author 1",
                "time": 1785482560,  # ~2026-07-30 — a recent-ish bookmark for realistic mock data`
                "site_name": "Example",
                "liked": False,
                "is_archived": False,
                "tags": ["tag1"],
                "notes": [],
            },
            {  # Intentionally sparse — tests _parse_bookmarks handling of missing optional fields
                "id": 2,
                "url": "https://example.com/2",
                "title": "Debug Article 2",
                "description": "",
            },
        ],
        "page": 1,
        "has_more": False,
    }

    # ---- Exercise the client ----
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, json=mock_session_response)
        m.get(INSTAPAPER_BOOKMARKS_URL, json=mock_bookmarks_response)

        try:
            articles, has_more = client.get_articles(page=1, add_article_preview=True)
        except Exception as exc:
            print(f"[ERROR] get_articles raised: {exc!r}")
            raise

        print(f"Fetched {len(articles)} articles. has_more: {has_more}")
        print()
        for article in articles:
            print(f"  [{article['id']}] {article['title']}")
            print(f"    URL: {article['url']}")
            if "article_preview" in article:
                print(f"    Preview: {article['article_preview']}")
            print()

    print("=== Debug helper finished ===")


if __name__ == "__main__":
    main()
