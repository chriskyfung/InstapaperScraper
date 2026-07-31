from unittest.mock import MagicMock
import pytest
from instapaper_scraper.api import InstapaperClient


@pytest.fixture
def mock_session():
    """Fixture for a mocked requests.Session."""
    return MagicMock()


def test_build_request_params_liked(mock_session):
    """Test that _build_request_params constructs liked folder params correctly."""
    client = InstapaperClient(mock_session)

    params = client._build_request_params(1, {"id": "liked"})
    assert params["section_type"] == "liked"
    assert params["page"] == 1
    assert params["sort"] == "newest"
    assert "folder_id" not in params

    params = client._build_request_params(2, {"id": "liked"})
    assert params["section_type"] == "liked"
    assert params["page"] == 2

    params = client._build_request_params(10, {"id": "liked"})
    assert params["section_type"] == "liked"
    assert params["page"] == 10


def test_build_request_params_archive(mock_session):
    """Test that _build_request_params constructs archive folder params correctly."""
    client = InstapaperClient(mock_session)

    params = client._build_request_params(1, {"id": "archive"})
    assert params["section_type"] == "archive"
    assert params["page"] == 1
    assert params["sort"] == "newest"
    assert "folder_id" not in params

    params = client._build_request_params(2, {"id": "archive"})
    assert params["section_type"] == "archive"
    assert params["page"] == 2

    params = client._build_request_params(10, {"id": "archive"})
    assert params["section_type"] == "archive"
    assert params["page"] == 10


def test_build_request_params_home(mock_session):
    """Test that _build_request_params constructs home params correctly."""
    client = InstapaperClient(mock_session)

    params = client._build_request_params(1, None)
    assert params["section_type"] == "home"
    assert params["page"] == 1
    assert params["sort"] == "newest"
    assert "folder_id" not in params


def test_build_request_params_custom_folder(mock_session):
    """Test that _build_request_params constructs custom folder params correctly."""
    client = InstapaperClient(mock_session)

    params = client._build_request_params(1, {"id": "12345", "slug": "my-folder"})
    assert params["section_type"] == "folder"
    assert params["page"] == 1
    assert params["sort"] == "newest"
    assert params["folder_id"] == "12345"
