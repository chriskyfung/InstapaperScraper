import pytest
import requests
import requests_mock
import logging
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup

from instapaper_scraper.api import InstapaperClient
from instapaper_scraper.exceptions import ScraperStructureChanged
from instapaper_scraper.constants import INSTAPAPER_BASE_URL, KEY_ID


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


def get_mock_html(page_num, has_more=True, malformed=False, no_articles=False):
    """Generates mock HTML for a page of articles."""
    articles_html = ""
    if not no_articles:
        for i in range(1, 3):
            article_id = (page_num - 1) * 2 + i
            if malformed and i == 2:
                articles_html += f"""
                <article id="article_{article_id}">
                    <div class="no_title">Article {article_id}</div>
                    <div class="title_meta"><a href="http://example.com/{article_id}">example.com</a></div>
                </article>
                """
            else:
                articles_html += f"""
                <article id="article_{article_id}">
                    <div class="article_title">Article {article_id}</div>
                    <div class="title_meta"><a href="http://example.com/{article_id}">example.com</a></div>
                </article>
                """

    pagination_html = (
        '<div class="paginate_older"><a>Older</a></div>' if has_more else ""
    )

    return f"""
    <html>
        <body>
            <div id="article_list">
                {articles_html}
            </div>
            {pagination_html}
        </body>
    </html>
    """


def test_get_articles_single_page_success(client, session):
    """Test successfully scraping a single page of articles."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            text=get_mock_html(page_num=1, has_more=True),
        )

        articles, has_more = client.get_articles(page=1)

        assert has_more is True
        assert len(articles) == 2
        assert_article_data(articles[0], "1", "Article 1", "http://example.com/1")
        assert_article_data(articles[1], "2", "Article 2", "http://example.com/2")


def test_get_articles_last_page(client, session):
    """Test scraping the last page of articles."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/2",
            text=get_mock_html(page_num=2, has_more=False),
        )

        articles, has_more = client.get_articles(page=2)

        assert has_more is False
        assert len(articles) == 2
        assert_article_data(articles[0], "3", "Article 3", "http://example.com/3")
        assert_article_data(articles[1], "4", "Article 4", "http://example.com/4")


def test_get_all_articles_multiple_pages(client, session):
    """Test iterating through multiple pages to get all articles."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            text=get_mock_html(page_num=1, has_more=True),
        )
        m.get(
            "https://www.instapaper.com/u/2",
            text=get_mock_html(page_num=2, has_more=False),
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
            m.get(
                "https://www.instapaper.com/u/1",
                text=get_mock_html(page_num=1, has_more=True),
            )

            all_articles = client.get_all_articles(limit=1)
            assert "Reached page limit of 1." in caplog.text

        assert len(all_articles) == 2
        assert_article_data(all_articles[0], "1", "Article 1", "http://example.com/1")
        assert_article_data(all_articles[1], "2", "Article 2", "http://example.com/2")


def test_get_all_articles_stops_at_limit(client, session, caplog):
    """Test that get_all_articles stops scraping when the limit is reached, even if more pages are available."""
    LIMIT = 3
    with caplog.at_level(logging.INFO):
        # Instead of mocking the URL directly, we mock the internal get_articles method
        # to control its return values and has_more flag.
        # This requires patching the method *on the instance*
        with patch.object(client, "get_articles") as mock_get_articles:
            mock_get_articles.side_effect = lambda page, folder_info: (
                ([{f"id_{page}_1": f"title_{page}_1"}], True)
                if page <= LIMIT + 5
                else ([], False)
            )

            # Set a limit such that it should trigger the logging.info
            # If limit is 1, and get_articles always returns has_more=True,
            # the loop will run for page=1, then page becomes 2, then page > limit (2 > 1) is true.
            all_articles = client.get_all_articles(limit=LIMIT)

            # The mock_get_articles should have been called LIMIT times.
            assert mock_get_articles.call_count == LIMIT
            assert (
                len(all_articles) == LIMIT
            )  # Articles from the first LIMIT pages should be collected


def test_unrecoverable_http_error_raises_exception(client, session, caplog):
    """Test that an unrecoverable HTTP error (e.g., 403) raises an exception."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", status_code=403)  # Forbidden

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError) as excinfo:
                client.get_articles(page=1)
            assert "Request failed with unrecoverable status code 403." in caplog.text
            assert excinfo.value.response.status_code == 403
        assert m.call_count == 1  # Should not retry


def test_parse_article_data_missing_article_element(client, caplog):
    """Test that _parse_article_data handles a missing article element by logging a warning and skipping it."""
    html = get_mock_html(page_num=1)  # Contains article_1 and article_2
    soup = BeautifulSoup(html, "html.parser")

    # article_ids will contain an ID that's not in the soup
    article_ids = ["1", "999"]  # 999 does not exist in the mock HTML

    with caplog.at_level(logging.WARNING):
        parsed_data = client._parse_article_data(soup, article_ids, page=1)

        assert len(parsed_data) == 1
        assert parsed_data[0][KEY_ID] == "1"
        assert "Article element 'article_999' not found." in caplog.text


@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_http_error_retries(client, session, status_code, caplog):
    """Test that the client retries on 5xx server errors."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"status_code": status_code},
                {"status_code": status_code},
                {"text": get_mock_html(1)},
            ],
        )

        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            articles, has_more = client.get_articles(page=1)
            assert f"Request failed with status {status_code}" in caplog.text

        assert m.call_count == 3
        assert len(articles) == 2


def test_http_error_all_retries_fail(client, session, caplog):
    """Test that an exception is raised after all retries fail for a 5xx error."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", status_code=500)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                client.get_articles(page=1)
            assert f"All {client.max_retries} retries failed." in caplog.text

        assert m.call_count == client.max_retries


def test_4xx_error_does_not_retry(client, session):
    """Test that client-side 4xx errors do not trigger a retry."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", status_code=404)

        with pytest.raises(requests.exceptions.HTTPError):
            client.get_articles(page=1)

        assert m.call_count == 1


def test_folder_mode_url_construction(client, session):
    """Test that the URL is correctly constructed when in folder mode."""
    with requests_mock.Mocker() as m:
        expected_url = "https://www.instapaper.com/u/folder/12345/my-folder/1"
        m.get(expected_url, text=get_mock_html(1))

        client.get_articles(page=1, folder_info={"id": "12345", "slug": "my-folder"})

        assert m.called
        assert m.last_request.url == expected_url


def test_429_error_with_retry_after(client, session, monkeypatch):
    """Test handling of 429 error with a Retry-After header."""
    with requests_mock.Mocker() as m:
        mock_sleep = MagicMock()
        monkeypatch.setattr("time.sleep", mock_sleep)

        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"status_code": 429, "headers": {"Retry-After": "5"}},
                {"text": get_mock_html(1)},
            ],
        )

        client.get_articles(page=1)

        assert m.call_count == 2
        mock_sleep.assert_called_once_with(5)


def test_malformed_article_is_skipped(client, session, caplog):
    """Test that a malformed article is skipped and a warning is logged."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            text=get_mock_html(page_num=1, malformed=True),
        )

        with caplog.at_level(logging.WARNING):
            articles, _ = client.get_articles(page=1)

            assert len(articles) == 1
            assert articles[0]["id"] == "1"
            assert "Could not parse article with id 2" in caplog.text


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
    "folder_info, expected_url_path",
    [
        (None, "/u/"),
        ({"id": "123", "slug": "test-folder"}, "/u/folder/123/test-folder/"),
        ({"id": "456"}, "/u/"),  # Missing slug, should fall back to user path
        (
            {"slug": "another-folder"},
            "/u/",
        ),  # Missing id, should fall back to user path
        ({}, "/u/"),  # Empty dict, should fall back to user path
    ],
)
def test_get_page_url(client, folder_info, expected_url_path):
    """Test _get_page_url constructs correct URLs for different folder_info."""
    page = 1
    expected_url = f"{INSTAPAPER_BASE_URL}{expected_url_path}{page}"
    assert client._get_page_url(page, folder_info) == expected_url


def test_get_articles_connection_error_retries(client, session, monkeypatch, caplog):
    """Test that get_articles retries on ConnectionError."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"exc": requests.exceptions.ConnectionError("Test error")},
                {"text": get_mock_html(1)},
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

        assert m.call_count == 2
        assert len(articles) == 2
        assert mock_sleep.call_count == 1


def test_get_articles_timeout_retries(client, session, monkeypatch):
    """Test that get_articles retries on Timeout."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"exc": requests.exceptions.Timeout},
                {"exc": requests.exceptions.Timeout},
                {"text": get_mock_html(1)},
            ],
        )

        client.max_retries = 3
        client.backoff_factor = 0.01

        articles, has_more = client.get_articles(page=1)

        assert m.call_count == 3
        assert len(articles) == 2
        assert mock_sleep.call_count == 2


def test_get_articles_all_retries_fail_connection_error(client, session, caplog):
    """Test that ConnectionError is re-raised after all retries fail."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", exc=requests.exceptions.ConnectionError)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_articles(page=1)
            assert "All 2 retries failed." in caplog.text

        assert m.call_count == 2


def test_get_articles_all_retries_fail_timeout(client, session):
    """Test that Timeout is re-raised after all retries fail."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", exc=requests.exceptions.Timeout)

        client.max_retries = 2
        client.backoff_factor = 0.01

        with pytest.raises(requests.exceptions.Timeout):
            client.get_articles(page=1)

        assert m.call_count == 2


def test_get_articles_handles_parsing_type_error(client, caplog, monkeypatch):
    """Test that a TypeError in _parse_article_data is handled."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)
    client.max_retries = 2
    client.backoff_factor = 0.01

    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", text=get_mock_html(1))

        with caplog.at_level(logging.WARNING):
            with patch.object(
                client, "_parse_article_data", side_effect=TypeError("Test Error")
            ):
                with pytest.raises(TypeError, match="Test Error"):
                    client.get_articles(page=1)
                assert (
                    "Scraping failed after multiple retries for an unknown reason"
                    in caplog.text
                )
    assert mock_sleep.call_count == client.max_retries


def test_get_articles_scraper_structure_changed_re_raise(client, session):
    """Test that ScraperStructureChanged is re-raised immediately."""
    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            text="<html><body>No article list</body></html>",
        )

        with pytest.raises(ScraperStructureChanged):
            client.get_articles(page=1)

        assert m.call_count == 1


def test_get_articles_unexpected_exception_after_retries(client, session, caplog):
    """Test that an unexpected exception is raised after all retries fail."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", exc=Exception("Unknown error"))

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception, match="Unknown error"):
                client.get_articles(page=1)
            assert "All 2 retries failed." in caplog.text

        assert m.call_count == 2


def test_handle_http_error_404_no_retry(client, session, caplog):
    """Test that a 404 error does not trigger a retry."""
    with requests_mock.Mocker() as m:
        m.get("https://www.instapaper.com/u/1", status_code=404)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                client.get_articles(page=1)

            assert "Error 404: Not Found" in caplog.text
            assert m.call_count == 1  # Only one call, no retry


def test_handle_http_error_429_no_retry_after_header(
    client, session, monkeypatch, caplog
):
    """Test handling of 429 error without Retry-After header, falls back to exponential backoff."""
    mock_sleep = MagicMock()
    monkeypatch.setattr("time.sleep", mock_sleep)

    with requests_mock.Mocker() as m:
        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"status_code": 429},  # No Retry-After header
                {"text": get_mock_html(1)},
            ],
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            articles, _ = client.get_articles(page=1)

            assert m.call_count == 2
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
        m.get(
            "https://www.instapaper.com/u/1",
            [
                {"status_code": 429, "headers": {"Retry-After": "invalid"}},
                {"text": get_mock_html(1)},
            ],
        )

        client.max_retries = 2
        client.backoff_factor = 0.01

        with caplog.at_level(logging.WARNING):
            client.get_articles(page=1)
            assert "Rate limited (429)" in caplog.text

        assert m.call_count == 2
        mock_sleep.assert_called_once()


def test_get_all_articles_reaches_limit(client, session, caplog):
    """Test that get_all_articles stops when the page limit is reached."""
    with caplog.at_level(logging.INFO):
        with requests_mock.Mocker() as m:
            m.get(
                "https://www.instapaper.com/u/1",
                text=get_mock_html(page_num=1, has_more=True),
            )
            m.get(
                "https://www.instapaper.com/u/2",
                text=get_mock_html(page_num=2, has_more=True),
            )
            client.get_all_articles(limit=1)
            assert "Reached page limit of 1." in caplog.text


def test_parse_article_data_missing_link_href(client, caplog):
    """Test parsing an article where the link element is missing the href attribute."""
    html = """
    <article id="article_1">
        <div class="article_title">Article 1</div>
        <div class="title_meta"><a>example.com</a></div>
    </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    with caplog.at_level(logging.WARNING):
        articles = client._parse_article_data(soup, ["1"], 1)
        assert len(articles) == 0
        assert "Could not parse article with id 1" in caplog.text
        assert "Link element or href not found" in caplog.text
