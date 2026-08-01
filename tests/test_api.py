import logging
import re
from unittest.mock import MagicMock, patch

import pytest
import requests
import requests_mock

from instapaper_scraper.api import InstapaperClient
from instapaper_scraper.constants import (
    INSTAPAPER_BOOKMARKS_URL,
    INSTAPAPER_USER_SESSION_URL,
)
from instapaper_scraper.exceptions import InstapaperAPIError


@pytest.fixture
def session():
    """Pytest fixture for a requests session."""
    return requests.Session()


@pytest.fixture
def client(session):
    """Pytest fixture for the InstapaperClient."""
    return InstapaperClient(session)


def assert_article_data(article, expected_id, expected_title, expected_url):
    """Helper to assert the structure and content of an article dictionary."""
    assert article["id"] == expected_id
    assert article["title"] == expected_title
    assert article["url"] == expected_url


def assert_article_preview_data(
    article, expected_id, expected_title, expected_url, expected_preview
):
    """Helper to assert the structure and content of an article dictionary with preview."""
    assert article["id"] == expected_id
    assert article["title"] == expected_title
    assert article["url"] == expected_url
    assert article["article_preview"] == expected_preview


def get_mock_bookmarks_json(
    page_num,
    has_more=True,
    with_preview=False,
    missing_preview=False,
    malformed=False,
):
    """Generates mock JSON response for a page of bookmarks."""
    bookmarks = []
    if not malformed:
        for i in range(1, 3):
            article_id = (page_num - 1) * 2 + i
            bm = {
                "id": article_id,
                "url": f"http://example.com/{article_id}",
                "title": f"Article {article_id}",
                "description": f"Preview for article {article_id}"
                if with_preview
                else "",
            }
            bm["description"] = bm.get("description", "")
            if missing_preview and i == 2:
                bm["description"] = ""
            bookmarks.append(bm)
    else:
        # Malformed: missing title for second bookmark
        bm1 = {
            "id": (page_num - 1) * 2 + 1,
            "url": f"http://example.com/{(page_num - 1) * 2 + 1}",
            "title": f"Article {(page_num - 1) * 2 + 1}",
        }
        bookmarks.append(bm1)
        bm2 = {
            "id": (page_num - 1) * 2 + 2,
            # title missing — triggers warning
        }
        bookmarks.append(bm2)

    return {"bookmarks": bookmarks, "page": page_num, "has_more": has_more}


def get_mock_session_json(form_key="test_form_key_1234567890"):
    """Generates mock JSON response for user_session."""
    return {
        "user": {
            "id": 12345,
            "email": "test@example.com",
            "username": "testuser",
            "form_key": form_key,
            "folders": [],
            "tags": [],
        }
    }


def setup_session_mock(m, form_key="test_form_key_1234567890"):
    """Helper to set up the user_session mock."""
    m.get(
        INSTAPAPER_USER_SESSION_URL,
        json=get_mock_session_json(form_key),
    )


def test_get_articles_single_page_success(client, session):
    """Test successfully fetching a single page of articles."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(page_num=1, has_more=True, with_preview=True),
        )

        articles, has_more = client.get_articles(page=1, add_article_preview=True)

        assert has_more is True
        assert len(articles) == 2
        assert_article_preview_data(
            articles[0],
            "1",
            "Article 1",
            "http://example.com/1",
            "Preview for article 1",
        )
        assert_article_preview_data(
            articles[1],
            "2",
            "Article 2",
            "http://example.com/2",
            "Preview for article 2",
        )


def test_get_articles_last_page(client, session):
    """Test fetching the last page of articles."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(page_num=2, has_more=False),
        )

        articles, has_more = client.get_articles(page=2)

        assert has_more is False
        assert len(articles) == 2
        assert_article_data(articles[0], "3", "Article 3", "http://example.com/3")
        assert_article_data(articles[1], "4", "Article 4", "http://example.com/4")


def test_get_all_articles_multiple_pages(client, session):
    """Test iterating through multiple pages to get all articles."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL + "?section_type=home&page=1&sort=newest",
            json=get_mock_bookmarks_json(page_num=1, has_more=True),
        )
        m.get(
            INSTAPAPER_BOOKMARKS_URL + "?section_type=home&page=2&sort=newest",
            json=get_mock_bookmarks_json(page_num=2, has_more=False),
        )

        all_articles = client.get_all_articles()

        assert len(all_articles) == 4
        assert_article_data(all_articles[0], "1", "Article 1", "http://example.com/1")
        assert_article_data(all_articles[1], "2", "Article 2", "http://example.com/2")
        assert_article_data(all_articles[2], "3", "Article 3", "http://example.com/3")
        assert_article_data(all_articles[3], "4", "Article 4", "http://example.com/4")


def test_get_all_articles_with_limit(client, session, caplog):
    """Test that get_all_articles respects the page limit."""
    with caplog.at_level(logging.INFO):
        with requests_mock.Mocker() as m:
            setup_session_mock(m)
            m.get(
                INSTAPAPER_BOOKMARKS_URL + "?section_type=home&page=1&sort=newest",
                json=get_mock_bookmarks_json(page_num=1, has_more=True),
            )

            all_articles = client.get_all_articles(limit=1)
            assert "Reached page limit of 1." in caplog.text

        assert len(all_articles) == 2
        assert_article_data(all_articles[0], "1", "Article 1", "http://example.com/1")
        assert_article_data(all_articles[1], "2", "Article 2", "http://example.com/2")


def test_get_all_articles_stops_at_limit(client, session, caplog):
    """Test that get_all_articles stops scraping when the limit is reached."""
    LIMIT = 3
    with caplog.at_level(logging.INFO):
        with patch.object(client, "get_articles") as mock_get_articles:
            mock_get_articles.side_effect = (
                lambda page, folder_info, add_article_preview: (
                    ([{f"id_{page}_1": f"title_{page}_1"}], True)
                    if page <= LIMIT + 5
                    else ([], False)
                )
            )

            all_articles = client.get_all_articles(limit=LIMIT)

            assert mock_get_articles.call_count == LIMIT
            assert len(all_articles) == LIMIT


def test_unrecoverable_http_error_raises_exception(client, session, caplog):
    """Test that an unrecoverable HTTP error (e.g., 403) raises an exception."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, status_code=403)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError) as excinfo:
                client.get_articles(page=1)
            assert "Request failed with unrecoverable status code 403." in caplog.text
            assert excinfo.value.response.status_code == 403
        assert m.call_count == 2  # session + 1 bookmarks


@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_http_error_retries(client, session, status_code, caplog):
    """Test that the client retries on 5xx server errors."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"status_code": status_code},
                {"status_code": status_code},
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            articles, has_more = client.get_articles(page=1)
            assert f"Request failed with status {status_code}" in caplog.text

        assert m.call_count == 4  # session + 3 bookmarks
        assert len(articles) == 2


def test_http_error_all_retries_fail(client, session, caplog):
    """Test that an exception is raised after all retries fail for a 5xx error."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, status_code=500)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                client.get_articles(page=1)
            assert f"All {client.max_retries} retries failed." in caplog.text

        assert m.call_count == 3  # session + 2 bookmarks


def test_4xx_error_does_not_retry(client, session):
    """Test that client-side 4xx errors do not trigger a retry."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, status_code=404)

        with pytest.raises(requests.exceptions.HTTPError):
            client.get_articles(page=1)

        assert m.call_count == 2  # session + 1 bookmarks


def test_folder_mode_request_params(client, session):
    """Test that the request params are correctly constructed when in folder mode."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(1),
        )

        client.get_articles(page=1, folder_info={"id": "12345", "slug": "my-folder"})

        assert m.called
        assert m.last_request.qs["section_type"] == ["folder"]
        assert m.last_request.qs["folder_id"] == ["12345"]
        assert m.last_request.qs["page"] == ["1"]


def test_429_error_with_retry_after(client, session, monkeypatch):
    """Test handling of 429 error with a Retry-After header."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        mock_sleep = MagicMock()
        monkeypatch.setattr("time.sleep", mock_sleep)

        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"status_code": 429, "headers": {"Retry-After": "5"}},
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.get_articles(page=1)

        assert m.call_count == 3  # session + 2 bookmarks
        mock_sleep.assert_called_with(5)


def test_malformed_article_is_handled(client, session, caplog):
    """Test that a malformed article (missing title) is handled gracefully."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(page_num=1, malformed=True),
        )

        with caplog.at_level(logging.WARNING):
            articles, _ = client.get_articles(page=1)

            assert len(articles) == 2
            assert articles[0]["id"] == "1"
            assert articles[0]["title"] == "Article 1"
            assert articles[1]["id"] == "2"
            assert articles[1]["title"] == ""
            assert "missing title" in caplog.text


def test_init_with_env_vars(monkeypatch, session):
    """Test InstapaperClient initialization with environment variables."""
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("BACKOFF_FACTOR", "2.0")
    client = InstapaperClient(session)
    assert client.max_retries == 5
    assert client.backoff_factor == 2.0


def test_init_with_invalid_env_vars_defaults(monkeypatch, session):
    """Test InstapaperClient initialization with invalid env vars falls back to defaults."""
    monkeypatch.setenv("MAX_RETRIES", "not_a_number")
    monkeypatch.setenv("BACKOFF_FACTOR", "not_a_float")
    client = InstapaperClient(session)
    assert client.max_retries == InstapaperClient.DEFAULT_MAX_RETRIES
    assert client.backoff_factor == InstapaperClient.DEFAULT_BACKOFF_FACTOR


@pytest.mark.parametrize(
    "folder_info, expected_section_type, expected_folder_id",
    [
        (None, "home", None),
        ({"id": "liked"}, "liked", None),
        ({"id": "archive"}, "archive", None),
        ({"id": "12345", "slug": "test-folder"}, "folder", "12345"),
        ({"id": "456"}, "folder", "456"),
    ],
)
def test_build_request_params(
    client, folder_info, expected_section_type, expected_folder_id
):
    """Test _build_request_params constructs correct params for different folder_info."""
    params = client._build_request_params(1, folder_info)
    assert params["section_type"] == expected_section_type
    assert params["page"] == 1
    assert params["sort"] == "newest"
    if expected_folder_id:
        assert params["folder_id"] == expected_folder_id
    else:
        assert "folder_id" not in params


def test_get_articles_connection_error_retries(client, session, monkeypatch, caplog):
    """Test that get_articles retries on ConnectionError."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"exc": requests.exceptions.ConnectionError("Test error")},
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            articles, has_more = client.get_articles(page=1)
            assert (
                "Network error (ConnectionError) (attempt 1/2). Retrying in 0.01 seconds."
                in caplog.text
            )

        assert m.call_count == 3  # session + 2 bookmarks
        assert len(articles) == 2
        assert mock_sleep.call_count == 1


def test_get_articles_timeout_retries(client, session, monkeypatch):
    """Test that get_articles retries on Timeout."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"exc": requests.exceptions.Timeout},
                {"exc": requests.exceptions.Timeout},
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.max_retries = 3
        client.backoff_factor = 0.01

        articles, has_more = client.get_articles(page=1)

        assert m.call_count == 4  # session + 3 bookmarks
        assert len(articles) == 2
        assert mock_sleep.call_count == 2


def test_get_articles_all_retries_fail_connection_error(
    client, session, caplog, monkeypatch
):
    """Test that ConnectionError is re-raised after all retries fail."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, exc=requests.exceptions.ConnectionError)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_articles(page=1)
            assert "All 2 retries failed." in caplog.text

        assert m.call_count == 3  # session + 2 bookmarks


def test_get_articles_all_retries_fail_timeout(client, session, monkeypatch):
    """Test that Timeout is re-raised after all retries fail."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, exc=requests.exceptions.Timeout)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with pytest.raises(requests.exceptions.Timeout):
            client.get_articles(page=1)

        assert m.call_count == 3  # session + 2 bookmarks


def test_get_articles_invalid_json_raises_instapaper_api_error(client, session):
    """Test that invalid JSON (missing bookmarks key) raises InstapaperAPIError."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json={"unexpected": "response"},
        )

        with pytest.raises(InstapaperAPIError):
            client.get_articles(page=1)


def test_get_articles_unexpected_exception_after_retries(
    client, session, caplog, monkeypatch
):
    """Test that an unexpected exception is raised after all retries fail."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, exc=Exception("Unknown error"))

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception, match="Unknown error"):
                client.get_articles(page=1)
            assert "All 2 retries failed." in caplog.text

        assert m.call_count == 3  # session + 2 bookmarks


def test_handle_http_error_404_no_retry(client, session, caplog):
    """Test that a 404 error does not trigger a retry."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(INSTAPAPER_BOOKMARKS_URL, status_code=404)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                client.get_articles(page=1)

            assert "Error 404: Not Found" in caplog.text
            assert m.call_count == 2  # session + 1 bookmarks


def test_handle_http_error_429_no_retry_after_header(
    client, session, monkeypatch, caplog
):
    """Test handling of 429 error without Retry-After header, falls back to exponential backoff."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"status_code": 429},  # No Retry-After header
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            articles, _ = client.get_articles(page=1)

            assert m.call_count == 3  # session + 2 bookmarks
            assert mock_sleep.call_count == 1
            assert (
                "Rate limited (429) (attempt 1/2). Retrying in 0.01 seconds."
                in caplog.text
            )
            assert len(articles) == 2


def test_http_error_429_with_invalid_retry_after(client, session, monkeypatch, caplog):
    """Test 429 error with an invalid Retry-After header."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            [
                {"status_code": 429, "headers": {"Retry-After": "invalid"}},
                {"json": get_mock_bookmarks_json(1)},
            ],
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            client.get_articles(page=1)
            assert "Rate limited (429)" in caplog.text

        assert m.call_count == 3  # session + 2 bookmarks
        mock_sleep.assert_called_once()


def test_get_all_articles_reaches_limit(client, session, caplog):
    """Test that get_all_articles stops when the page limit is reached."""
    with caplog.at_level(logging.INFO), requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL + "?section_type=home&page=1&sort=newest",
            json=get_mock_bookmarks_json(page_num=1, has_more=True),
        )
        m.get(
            INSTAPAPER_BOOKMARKS_URL + "?section_type=home&page=2&sort=newest",
            json=get_mock_bookmarks_json(page_num=2, has_more=True),
        )
        client.get_all_articles(limit=1)
        assert "Reached page limit of 1." in caplog.text


def test_get_articles_with_preview(client, session):
    """Test that the article preview is included when requested."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(page_num=1, with_preview=True),
        )
        articles, _ = client.get_articles(page=1, add_article_preview=True)
        assert len(articles) == 2
        assert_article_preview_data(
            articles[0],
            "1",
            "Article 1",
            "http://example.com/1",
            "Preview for article 1",
        )
        assert_article_preview_data(
            articles[1],
            "2",
            "Article 2",
            "http://example.com/2",
            "Preview for article 2",
        )


def test_get_articles_with_preview_missing(client, session):
    """Test that a missing article preview is handled gracefully."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(
                page_num=1, with_preview=True, missing_preview=True
            ),
        )
        articles, _ = client.get_articles(page=1, add_article_preview=True)
        assert len(articles) == 2
        assert_article_preview_data(
            articles[0],
            "1",
            "Article 1",
            "http://example.com/1",
            "Preview for article 1",
        )
        assert_article_preview_data(
            articles[1], "2", "Article 2", "http://example.com/2", ""
        )


def test_get_articles_without_preview(client, session):
    """Test that the article preview is not included when not requested."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(page_num=1, with_preview=True),
        )
        articles, _ = client.get_articles(page=1, add_article_preview=False)
        assert len(articles) == 2
        assert "article_preview" not in articles[0]
        assert "article_preview" not in articles[1]


def test_fetch_form_key_already_cached(client, session):
    """Test that _fetch_form_key returns immediately if form_key is already cached."""
    client._form_key = "existing_key"
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL)
        client._fetch_form_key()
        assert m.call_count == 0  # No HTTP request made
        assert client._form_key == "existing_key"


def test_fetch_form_key_non_json_response(client, session):
    """Test that _fetch_form_key handles non-JSON response gracefully."""
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            text="<html>not json</html>",
        )
        client._fetch_form_key()
        assert client._form_key is None


def test_fetch_form_key_network_error(client, session):
    """Test that _fetch_form_key handles network errors gracefully."""
    with requests_mock.Mocker() as m:
        m.get(INSTAPAPER_USER_SESSION_URL, exc=requests.exceptions.ConnectionError)
        client._fetch_form_key()
        assert client._form_key is None


def test_parse_bookmarks_exception_during_parsing(client, caplog):
    """Test that an exception during bookmark parsing is caught and the bookmark is skipped."""

    # Create a bookmark that will cause an exception during parsing
    # by making a custom dict that raises on .get() for non-id keys
    class BadDict(dict):
        def get(self, key, default=None):
            if key == "id":
                return "bad_bookmark"
            raise ValueError("Simulated data-shape error")

    bookmarks = [
        {
            "id": 1,
            "url": "http://example.com/1",
            "title": "Article 1",
        },
        BadDict(),
    ]

    with caplog.at_level(logging.WARNING):
        articles = client._parse_bookmarks(bookmarks, add_article_preview=False)

    assert len(articles) == 1
    assert articles[0]["id"] == "1"
    assert "Could not parse bookmark" in caplog.text


def test_get_articles_all_retries_fail_no_last_exception(
    client, session, caplog, monkeypatch
):
    """Test that a generic Exception is raised when all retries fail and last_exception is None."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    # Mock _parse_bookmarks to raise an exception that gets caught by the generic except Exception
    def failing_parse(bookmarks, add_article_preview):
        raise Exception("Simulated parse failure")

    monkeypatch.setattr(client, "_parse_bookmarks", failing_parse)

    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(1),
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception, match="Simulated parse failure"):
                client.get_articles(page=1)
            assert "All 2 retries failed." in caplog.text

        assert m.call_count == 3  # session + 2 bookmarks


def test_url_safe_pattern_is_compiled_regex():
    """Test that URL_SAFE_PATTERN is a compiled regex object."""
    assert isinstance(InstapaperClient.URL_SAFE_PATTERN, re.Pattern)


def test_form_key_is_cached(client, session):
    """Test that form_key is fetched once and cached."""
    with requests_mock.Mocker() as m:
        m.get(
            INSTAPAPER_USER_SESSION_URL,
            json=get_mock_session_json("my_form_key"),
        )
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json=get_mock_bookmarks_json(1),
        )

        client.get_articles(page=1)
        assert m.call_count == 2  # session + bookmarks

        client.get_articles(page=2)
        # Second call should NOT fetch form_key again
        assert m.call_count == 3
        assert client._form_key == "my_form_key"


def test_rich_metadata_included(client, session):
    """Test that rich metadata fields from JSON are included in article dict."""
    with requests_mock.Mocker() as m:
        setup_session_mock(m)
        m.get(
            INSTAPAPER_BOOKMARKS_URL,
            json={
                "bookmarks": [
                    {
                        "id": 1,
                        "url": "http://example.com/1",
                        "title": "Article 1",
                        "description": "Preview",
                        "author": "Author Name",
                        "time": 1785482560,
                        "site_name": "Example",
                        "liked": False,
                        "is_archived": False,
                        "tags": ["tag1"],
                        "notes": [],
                    }
                ],
                "page": 1,
                "has_more": False,
            },
        )
        articles, _ = client.get_articles(page=1, add_article_preview=True)

        assert articles[0]["author"] == "Author Name"
        assert articles[0]["time"] == 1785482560
        assert articles[0]["site_name"] == "Example"
        assert articles[0]["liked"] is False
        assert articles[0]["is_archived"] is False
        assert articles[0]["tags"] == ["tag1"]
        assert articles[0]["notes"] == []
