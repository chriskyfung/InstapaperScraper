import os
import logging
import time
from typing import List, Dict, Tuple, Optional

import requests
from bs4 import BeautifulSoup

from .exceptions import ScraperStructureChanged


class InstapaperClient:
    """
    A client for interacting with the Instapaper website to fetch articles.
    """

    BASE_URL = "https://www.instapaper.com"

    def __init__(self, session: requests.Session):
        """
        Initializes the client with a requests Session.
        Args:
            session: A requests.Session object, presumably authenticated.
        """
        self.session = session
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
        self.backoff_factor = float(os.getenv("BACKOFF_FACTOR", 1))

    def get_articles(self, page: int = 1) -> Tuple[List[Dict[str, str]], bool]:
        """
        Fetches a single page of articles and determines if there are more pages.
        Args:
            page: The page number to fetch.
        Returns:
            A tuple containing:
            - A list of article data (dictionaries with id, title, url).
            - A boolean indicating if there is a next page.
        """
        url = self._get_page_url(page)
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                article_list = soup.find(id="article_list")
                if not article_list:
                    raise ScraperStructureChanged(
                        "Could not find article list ('#article_list')."
                    )

                articles = article_list.find_all("article")
                article_ids = [
                    article["id"].replace("article_", "") for article in articles
                ]

                data = self._parse_article_data(soup, article_ids, page)
                has_more = soup.find(class_="paginate_older") is not None

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
                self._wait_for_retry(attempt, f"Network error ({type(e).__name__})")

            except ScraperStructureChanged as e:
                logging.error(f"Scraping failed due to HTML structure change: {e}")
                raise e

        logging.error(f"All {self.max_retries} retries failed.")
        if last_exception:
            raise last_exception
        raise Exception("Scraping failed after multiple retries for an unknown reason.")

    def get_all_articles(self) -> List[Dict[str, str]]:
        """
        Iterates through all pages and fetches all articles.
        """
        all_articles = []
        page = 1
        has_more = True
        while has_more:
            logging.info(f"Scraping page {page}...")
            data, has_more = self.get_articles(page=page)
            if data:
                all_articles.extend(data)
            page += 1
        return all_articles

    def _get_page_url(self, page: int) -> str:
        """Constructs the URL for the given page, considering folder mode."""
        enable_folder_mode = os.getenv("ENABLE_FOLDER_MODE", "false").lower() in (
            "true",
            "1",
            "t",
        )
        folder_id_and_slug = os.getenv("FOLDER_ID_AND_SLUG")

        if enable_folder_mode and folder_id_and_slug:
            return f"{self.BASE_URL}/u/folder/{folder_id_and_slug}/{page}"
        return f"{self.BASE_URL}/u/{page}"

    def _parse_article_data(
        self, soup: BeautifulSoup, article_ids: List[str], page: int
    ) -> List[Dict[str, str]]:
        """Parses the raw HTML to extract structured data for each article."""
        data = []
        for article_id in article_ids:
            article_element = soup.find(id=f"article_{article_id}")
            try:
                if not article_element:
                    raise AttributeError(
                        f"Article element 'article_{article_id}' not found."
                    )

                title_element = article_element.find(class_="article_title")
                if not title_element:
                    raise AttributeError("Title element not found")
                title = title_element.get_text().strip()

                link_element = article_element.find(class_="title_meta").find("a")
                if not link_element or "href" not in link_element.attrs:
                    raise AttributeError("Link element or href not found")
                link = link_element["href"]

                data.append({"id": article_id, "title": title, "url": link})
            except AttributeError as e:
                logging.warning(
                    f"Could not parse article with id {article_id} on page {page}. Details: {e}"
                )
                continue
        return data

    def _handle_http_error(
        self, e: requests.exceptions.HTTPError, attempt: int
    ) -> bool:
        """Handles HTTP errors, returns True if a retry should be attempted."""
        status_code = e.response.status_code
        if status_code == 429:  # Too Many Requests
            wait_time_str = e.response.headers.get("Retry-After")
            try:
                wait_time = int(wait_time_str) if wait_time_str else 0
                if wait_time > 0:
                    logging.warning(
                        f"Rate limited (429). Retrying after {wait_time} seconds."
                    )
                    time.sleep(wait_time)
                    return True
            except (ValueError, TypeError):
                pass  # Fallback to exponential backoff
            self._wait_for_retry(attempt, "Rate limited (429)")
            return True
        elif 500 <= status_code < 600:  # Server-side errors
            self._wait_for_retry(attempt, f"Request failed with status {status_code}")
            return True
        else:  # Other client-side errors (4xx) are not worth retrying
            logging.error(
                f"Request failed with unrecoverable status code {status_code}."
            )
            return False

    def _wait_for_retry(self, attempt: int, reason: str):
        """Calculates and waits for an exponential backoff period."""
        sleep_time = self.backoff_factor * (2**attempt)
        logging.warning(
            f"{reason} (attempt {attempt + 1}/{self.max_retries}). Retrying in {sleep_time:.2f} seconds."
        )
        time.sleep(sleep_time)
