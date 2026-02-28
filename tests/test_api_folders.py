from unittest.mock import MagicMock
import pytest
from instapaper_scraper.api import InstapaperClient


@pytest.fixture
def mock_session():
    """Fixture for a mocked requests.Session."""
    return MagicMock()


def test_get_page_url_liked(mock_session):
    """Test that _get_page_url constructs liked folder URLs correctly."""
    client = InstapaperClient(mock_session)

    # Test first page
    url_page_1 = client._get_page_url(1, {"id": "liked"})
    assert url_page_1 == "https://www.instapaper.com/liked"

    # Test second page
    url_page_2 = client._get_page_url(2, {"id": "liked"})
    assert url_page_2 == "https://www.instapaper.com/liked/2"

    # Test another page
    url_page_10 = client._get_page_url(10, {"id": "liked"})
    assert url_page_10 == "https://www.instapaper.com/liked/10"


def test_get_page_url_archive(mock_session):
    """Test that _get_page_url constructs archive folder URLs correctly."""
    client = InstapaperClient(mock_session)

    # Test first page
    url_page_1 = client._get_page_url(1, {"id": "archive"})
    assert url_page_1 == "https://www.instapaper.com/archive"

    # Test second page
    url_page_2 = client._get_page_url(2, {"id": "archive"})
    assert url_page_2 == "https://www.instapaper.com/archive/2"

    # Test another page
    url_page_10 = client._get_page_url(10, {"id": "archive"})
    assert url_page_10 == "https://www.instapaper.com/archive/10"
