import os
import logging
import time
from typing import List, Dict, Tuple, Optional, Any

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .exceptions import ScraperStructureChanged
from .constants import INSTAPAPER_BASE_URL, KEY_ID, KEY_TITLE, KEY_URL


class InstapaperClient:
    """
    A client for interacting with the Instapaper website to fetch articles.
    """

    # Environment variable names
    ENV_MAX_RETRIES = "MAX_RETRIES"
    ENV_BACKOFF_FACTOR = "BACKOFF_FACTOR"

    # Default values
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 1.0
    DEFAULT_REQUEST_TIMEOUT = 30
    DEFAULT_PAGE_START = 1

    # HTML parsing constants
    HTML_PARSER = "html.parser"
    ARTICLE_LIST_ID = "article_list"
    ARTICLE_TAG = "article"
    ARTICLE_ID_PREFIX = "article_"
    PAGINATE_OLDER_CLASS = "paginate_older"
    ARTICLE_TITLE_CLASS = "article_title"
    TITLE_META_CLASS = "title_meta"

    # URL paths
    URL_PATH_USER = "/u/"
    URL_PATH_FOLDER = "/u/folder/"

    # HTTP status codes
    HTTP_TOO_MANY_REQUESTS = 429
    HTTP_SERVER_ERROR_START = 500
    HTTP_SERVER_ERROR_END = 600

    # Logging and error messages
    MSG_ARTICLE_LIST_NOT_FOUND = "Could not find article list ('#article_list')."
    MSG_SCRAPING_PAGE = "Scraping page {page}..."
    MSG_ARTICLE_ELEMENT_NOT_FOUND = "Article element '{article_id_full}' not found."
    MSG_TITLE_ELEMENT_NOT_FOUND = "Title element not found"
    MSG_LINK_ELEMENT_NOT_FOUND = "Link element or href not found"
    MSG_PARSE_ARTICLE_WARNING = (
        "Could not parse article with id {article_id} on page {page}. Details: {e}"
    )
    MSG_RATE_LIMITED_RETRY = (
        "Rate limited ({status_code}). Retrying after {wait_time} seconds."
    )
    MSG_RATE_LIMITED_REASON = "Rate limited ({status_code})"
    MSG_REQUEST_FAILED_STATUS_REASON = "Request failed with status {status_code}"
    MSG_REQUEST_FAILED_UNRECOVERABLE = (
        "Request failed with unrecoverable status code {status_code}."
    )
    MSG_NETWORK_ERROR_REASON = "Network error ({error_type})"
    MSG_SCRAPING_FAILED_STRUCTURE_CHANGE = (
        "Scraping failed due to HTML structure change: {e}"
    )
    MSG_ALL_RETRIES_FAILED = "All {max_retries} retries failed."
    MSG_SCRAPING_FAILED_UNKNOWN = (
        "Scraping failed after multiple retries for an unknown reason."
    )
    MSG_RETRY_ATTEMPT = "{reason} (attempt {attempt_num}/{max_retries}). Retrying in {sleep_time:.2f} seconds."

    def __init__(self, session: requests.Session):
        """
        Initializes the client with a requests Session.
        Args:
            session: A requests.Session object, presumably authenticated.
        """
        self.session = session
        try:
            self.max_retries = int(
                os.getenv(self.ENV_MAX_RETRIES, str(self.DEFAULT_MAX_RETRIES))
            )
        except ValueError:
            logging.warning(
                f"Invalid value for {self.ENV_MAX_RETRIES}, using default {self.DEFAULT_MAX_RETRIES}"
            )
            self.max_retries = self.DEFAULT_MAX_RETRIES

        try:
            self.backoff_factor = float(
                os.getenv(self.ENV_BACKOFF_FACTOR, str(self.DEFAULT_BACKOFF_FACTOR))
            )
        except ValueError:
            logging.warning(
                f"Invalid value for {self.ENV_BACKOFF_FACTOR}, using default {self.DEFAULT_BACKOFF_FACTOR}"
            )
            self.backoff_factor = self.DEFAULT_BACKOFF_FACTOR

    def get_articles(
        self,
        page: int = DEFAULT_PAGE_START,
        folder_info: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[Dict[str, str]], bool]:
        """
        Fetches a single page of articles and determines if there are more pages.
        Args:
            page: The page number to fetch.
            folder_info: A dictionary containing 'id' and 'slug' of the folder to fetch articles from.
        Returns:
            A tuple containing:
            - A list of article data (dictionaries with id, title, url).
            - A boolean indicating if there is a next page.
        """
        url = self._get_page_url(page, folder_info)
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.DEFAULT_REQUEST_TIMEOUT)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, self.HTML_PARSER)

                article_list = soup.find(id=self.ARTICLE_LIST_ID)
                if not isinstance(article_list, Tag):
                    raise ScraperStructureChanged(self.MSG_ARTICLE_LIST_NOT_FOUND)

                articles = article_list.find_all(self.ARTICLE_TAG)
                article_ids = []
                for article in articles:
                    if not isinstance(article, Tag):
                        continue
                    article_id_val = article.get(KEY_ID)

                    # Ensure article_id_val is a string before calling replace
                    # If it's a list, take the first element. This is a pragmatic
                    # approach since 'id' attributes should ideally be unique strings.
                    if isinstance(article_id_val, list):
                        article_id_val = article_id_val[0] if article_id_val else None

                    if isinstance(article_id_val, str) and article_id_val.startswith(
                        self.ARTICLE_ID_PREFIX
                    ):
                        article_ids.append(
                            article_id_val.replace(self.ARTICLE_ID_PREFIX, "")
                        )

                data = self._parse_article_data(soup, article_ids, page)
                has_more = soup.find(class_=self.PAGINATE_OLDER_CLASS) is not None

                return data, has_more

            except requests.exceptions.HTTPError as e:
                last_exception = e
                if self._handle_http_error(e, attempt):
                    continue  # Retry if the handler decided to wait
                else:
                    raise e  # Re-raise if the error is unrecoverable

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                last_exception = e
                self._wait_for_retry(
                    attempt,
                    self.MSG_NETWORK_ERROR_REASON.format(error_type=type(e).__name__),
                )

            except ScraperStructureChanged as e:
                logging.error(self.MSG_SCRAPING_FAILED_STRUCTURE_CHANGE.format(e=e))
                raise e
            except Exception as e:
                last_exception = e
                self._wait_for_retry(
                    attempt,
                    self.MSG_SCRAPING_FAILED_UNKNOWN,
                )

        logging.error(self.MSG_ALL_RETRIES_FAILED.format(max_retries=self.max_retries))
        if last_exception:
            raise last_exception
        raise Exception(self.MSG_SCRAPING_FAILED_UNKNOWN)

    def get_all_articles(
        self, limit: Optional[int] = None, folder_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, str]]:
        """
        Iterates through pages and fetches articles up to a specified limit.
        Args:
            limit: The maximum number of pages to scrape. If None, scrapes all pages.
            folder_info: A dictionary containing 'id' and 'slug' of the folder to fetch articles from.
        """
        all_articles = []
        page = self.DEFAULT_PAGE_START
        has_more = True
        while has_more:
            if limit is not None and page > limit:
                logging.info(f"Reached page limit of {limit}.")
                break

            logging.info(self.MSG_SCRAPING_PAGE.format(page=page))
            data, has_more = self.get_articles(page=page, folder_info=folder_info)
            if data:
                all_articles.extend(data)
            page += 1
        return all_articles

    def _get_page_url(
        self, page: int, folder_info: Optional[Dict[str, str]] = None
    ) -> str:
        """Constructs the URL for the given page, considering folder mode."""
        if folder_info and folder_info.get("id") and folder_info.get("slug"):
            return f"{INSTAPAPER_BASE_URL}{self.URL_PATH_FOLDER}{folder_info['id']}/{folder_info['slug']}/{page}"
        return f"{INSTAPAPER_BASE_URL}{self.URL_PATH_USER}{page}"

    def _parse_article_data(
        self, soup: BeautifulSoup, article_ids: List[str], page: int
    ) -> List[Dict[str, Any]]:
        """Parses the raw HTML to extract structured data for each article."""
        data = []
        for article_id in article_ids:
            article_id_full = f"{self.ARTICLE_ID_PREFIX}{article_id}"
            article_element = soup.find(id=article_id_full)
            try:
                if not isinstance(article_element, Tag):
                    raise AttributeError(
                        self.MSG_ARTICLE_ELEMENT_NOT_FOUND.format(
                            article_id_full=article_id_full
                        )
                    )

                title_element = article_element.find(class_=self.ARTICLE_TITLE_CLASS)
                if not isinstance(title_element, Tag):
                    raise AttributeError(self.MSG_TITLE_ELEMENT_NOT_FOUND)
                title = title_element.get_text().strip()

                meta_element = article_element.find(class_=self.TITLE_META_CLASS)
                if not isinstance(meta_element, Tag):
                    raise AttributeError(self.MSG_LINK_ELEMENT_NOT_FOUND)

                link_element = meta_element.find("a")
                if (
                    not isinstance(link_element, Tag)
                    or "href" not in link_element.attrs
                ):
                    raise AttributeError(self.MSG_LINK_ELEMENT_NOT_FOUND)
                link = link_element["href"]

                data.append({KEY_ID: article_id, KEY_TITLE: title, KEY_URL: link})
            except AttributeError as e:
                logging.warning(
                    self.MSG_PARSE_ARTICLE_WARNING.format(
                        article_id=article_id, page=page, e=e
                    )
                )
                continue
        return data

    def _handle_http_error(
        self, e: requests.exceptions.HTTPError, attempt: int
    ) -> bool:
        """Handles HTTP errors, returns True if a retry should be attempted."""
        status_code = e.response.status_code
        if status_code == self.HTTP_TOO_MANY_REQUESTS:  # Too Many Requests
            wait_time_str = e.response.headers.get("Retry-After")
            try:
                wait_time = int(wait_time_str) if wait_time_str else 0
                if wait_time > 0:
                    logging.warning(
                        self.MSG_RATE_LIMITED_RETRY.format(
                            status_code=status_code, wait_time=wait_time
                        )
                    )
                    time.sleep(wait_time)
                    return True
            except (ValueError, TypeError):
                pass  # Fallback to exponential backoff
            self._wait_for_retry(
                attempt, self.MSG_RATE_LIMITED_REASON.format(status_code=status_code)
            )
            return True
        elif (
            self.HTTP_SERVER_ERROR_START <= status_code < self.HTTP_SERVER_ERROR_END
        ):  # Server-side errors
            self._wait_for_retry(
                attempt,
                self.MSG_REQUEST_FAILED_STATUS_REASON.format(status_code=status_code),
            )
            return True
        elif status_code == 404:
            logging.error(
                f"Error 404: Not Found. This might indicate an invalid folder ID or slug. URL: {e.response.url}"
            )
            return False  # Do not retry, unrecoverable
        else:  # Other client-side errors (4xx) are not worth retrying
            logging.error(
                self.MSG_REQUEST_FAILED_UNRECOVERABLE.format(status_code=status_code)
            )
            return False

    def _wait_for_retry(self, attempt: int, reason: str) -> None:
        """Calculates and waits for an exponential backoff period."""
        sleep_time = self.backoff_factor * (2**attempt)
        logging.warning(
            self.MSG_RETRY_ATTEMPT.format(
                reason=reason,
                attempt_num=attempt + 1,
                max_retries=self.max_retries,
                sleep_time=sleep_time,
            )
        )
        time.sleep(sleep_time)
