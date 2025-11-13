import unittest
import os
import requests
import logging
import time
from unittest.mock import patch, MagicMock, Mock
from bs4 import BeautifulSoup

# Assuming scrape.py is in the same directory or in python path
from scrape import GetArticleIDs, ScraperStructureChanged, Application

# Sample HTML for mocking responses
SAMPLE_HTML_OK = """
<div id="article_list">
    <article id="article_123">
        <div class="article_title">Test Title 1</div>
        <div class="title_meta"><a href="http://example.com/1"></a></div>
    </article>
    <article id="article_456">
        <div class="article_title">Test Title 2</div>
        <div class="title_meta"><a href="http://example.com/2"></a></div>
    </article>
    <div class="paginate_older"></div>
</div>
"""

SAMPLE_HTML_MISSING_LIST = """
<div>Some other content</div>
"""

SAMPLE_HTML_MALFORMED_ARTICLE = """
<div id="article_list">
    <article id="article_123">
        <div class="article_title">Test Title 1</div>
        <div class="title_meta"><a href="http://example.com/1"></a></div>
    </article>
    <article id="article_789">
        <!-- Missing title -->
        <div class="title_meta"><a href="http://example.com/3"></a></div>
    </article>
</div>
"""

class TestGetArticleIDs(unittest.TestCase):

    def setUp(self):
        """Set up a test environment before each test."""
        # Mock the requests.Session object that will be used as the "driver"
        self.mock_session = MagicMock(spec=requests.Session)
        
        # The Application class holds the driver
        self.app = Application(self.mock_session)
        
        # Set environment variables for faster tests
        os.environ["MAX_RETRIES"] = "2"
        os.environ["BACKOFF_FACTOR"] = "0.01"

        # Suppress logging output during tests
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        """Clean up after each test."""
        # Restore logging
        logging.disable(logging.NOTSET)
        # Clean up environment variables
        del os.environ["MAX_RETRIES"]
        del os.environ["BACKOFF_FACTOR"]

    def test_successful_scrape(self):
        """Test the happy path with a successful response."""
        # Configure the mock session to return a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML_OK
        self.mock_session.get.return_value = mock_response

        # Execute the transaction
        ids, data, has_more = self.app.at(GetArticleIDs, page=1).result

        # Assertions
        self.mock_session.get.assert_called_once()
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids, ["123", "456"])
        self.assertEqual(data[0]['title'], "Test Title 1")
        self.assertTrue(has_more)

    @patch('time.sleep')
    def test_retry_on_5xx_error(self, mock_sleep):
        """Test that the request is retried on a 503 server error."""
        # First call raises 503, second call is successful
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_fail)

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.text = SAMPLE_HTML_OK

        self.mock_session.get.side_effect = [mock_response_fail, mock_response_ok]

        # Execute
        _, data, _ = self.app.at(GetArticleIDs, page=1).result

        # Assertions
        self.assertEqual(self.mock_session.get.call_count, 2)
        mock_sleep.assert_called_once() # Should have slept once
        self.assertEqual(len(data), 2)

    @patch('time.sleep')
    def test_max_retries_exceeded(self, mock_sleep):
        """Test that an exception is raised after all retries fail."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_fail)

        self.mock_session.get.return_value = mock_response_fail

        # Execute and assert that it raises the final exception
        with self.assertRaises(requests.exceptions.HTTPError):
            self.app.at(GetArticleIDs, page=1).result

        # Assertions
        max_retries = int(os.environ["MAX_RETRIES"])
        self.assertEqual(self.mock_session.get.call_count, max_retries)
        self.assertEqual(mock_sleep.call_count, max_retries)

    def test_html_structure_change_raises_exception(self):
        """Test that ScraperStructureChanged is raised if the article list is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML_MISSING_LIST
        self.mock_session.get.return_value = mock_response

        with self.assertRaises(ScraperStructureChanged):
            self.app.at(GetArticleIDs, page=1).result

    @patch('scrape.logging')
    def test_malformed_article_is_skipped(self, mock_logging):
        """Test that a malformed article is skipped and a warning is logged."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_HTML_MALFORMED_ARTICLE
        self.mock_session.get.return_value = mock_response

        _, data, _ = self.app.at(GetArticleIDs, page=1).result

        # Assertions
        self.assertEqual(len(data), 1) # Only the valid article should be parsed
        self.assertEqual(data[0]['id'], "123")
        mock_logging.warning.assert_called_once() # Check that a warning was logged

    @patch('time.sleep')
    def test_429_error_with_retry_after(self, mock_sleep):
        """Test handling of 429 error with a Retry-After header."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '5'}
        mock_response_429.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_429)

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.text = SAMPLE_HTML_OK

        self.mock_session.get.side_effect = [mock_response_429, mock_response_ok]

        self.app.at(GetArticleIDs, page=1).result

        # Assertions
        self.assertEqual(self.mock_session.get.call_count, 2)
        mock_sleep.assert_called_with(5) # Should sleep for the duration from the header

    def test_unrecoverable_4xx_error(self):
        """Test that a 404 error is not retried."""
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        mock_response_404.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response_404)
        self.mock_session.get.return_value = mock_response_404

        with self.assertRaises(requests.exceptions.HTTPError):
            self.app.at(GetArticleIDs, page=1).result

        self.mock_session.get.assert_called_once() # Should not retry

if __name__ == '__main__':
    unittest.main()
