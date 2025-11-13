#!/usr/bin/env python
# coding: utf-8

import os
import requests
import sys
import logging
import getpass
import stat
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from guara.transaction import AbstractTransaction, Application
from cryptography.fernet import Fernet

load_dotenv()

# --- Custom Exception ---
class ScraperStructureChanged(Exception):
    """Custom exception for when the scraper detects an HTML structure change."""
    pass

# --- Encryption Helper ---
def get_encryption_key(key_file=".session_key"):
    """
    Loads the encryption key from a file or generates a new one.
    Sets strict file permissions for the key file.
    """
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        # Set file permissions to 0600 (owner read/write only)
        os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
        logging.info(f"Generated new encryption key at {key_file}.")
    return key

class GetArticleIDs(AbstractTransaction):
    """
    Fetches article IDs and metadata from Instapaper.

    Args:
        page (int): Page number to fetch.

    Returns:
        tuple: (ids, data, has_more)
    """
    def do(self, page):
        enable_folder_mode = os.getenv("ENABLE_FOLDER_MODE", False).lower() in ("true", "1", "t")
        folder_id_and_slug = os.getenv("FOLDER_ID_AND_SLUG")

        if enable_folder_mode:
            url = f"https://www.instapaper.com/u/folder/{folder_id_and_slug}/{page}"
        else:
            url = f"https://www.instapaper.com/u/{page}"

        max_retries = int(os.getenv("MAX_RETRIES", 3))
        backoff_factor = float(os.getenv("BACKOFF_FACTOR", 1))
        last_exception = None

        for attempt in range(max_retries):
            try:
                r = self._driver.get(url, timeout=30)  # Add a timeout
                r.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)

                # If successful, proceed with parsing
                soup = BeautifulSoup(r.text, "html.parser")

                article_list = soup.find(id="article_list")
                if not article_list:
                    raise ScraperStructureChanged("Could not find article list ('#article_list'). The page structure may have changed.")

                articles = article_list.find_all("article")
                ids = [i["id"].replace("article_", "") for i in articles]

                data = []
                for i in ids:
                    article = soup.find(id="article_" + i)
                    try:
                        title_element = article.find(class_="article_title")
                        if not title_element:
                            raise AttributeError("Title element not found")
                        title = title_element.getText().strip()

                        link_element = article.find(class_="title_meta").find("a")
                        if not link_element or 'href' not in link_element.attrs:
                            raise AttributeError("Link element or href not found")
                        link = link_element["href"]

                        data.append({
                            "id": i,
                            "title": title,
                            "url": link
                        })
                    except AttributeError as e:
                        logging.warning(f"Could not parse article with id {i} on page {page}. HTML structure might have changed. Details: {e}")
                        continue  # Skip this article

                has_more = soup.find(class_="paginate_older") is not None
                return ids, data, has_more

            except requests.exceptions.HTTPError as e:
                last_exception = e
                status_code = e.response.status_code

                if status_code == 429:  # Too Many Requests
                    wait_time = int(e.response.headers.get("Retry-After", 0))
                    if wait_time > 0:
                        logging.warning(f"Rate limited (429). Retrying after {wait_time} seconds as per Retry-After header.")
                        time.sleep(wait_time)
                    else:
                        sleep_time = backoff_factor * (2 ** attempt)
                        logging.warning(f"Rate limited (429). No Retry-After header. Retrying in {sleep_time:.2f} seconds.")
                        time.sleep(sleep_time)
                elif 500 <= status_code < 600:  # Server-side errors
                    sleep_time = backoff_factor * (2 ** attempt)
                    logging.warning(f"Request failed with status {status_code} (attempt {attempt + 1}/{max_retries}). Retrying in {sleep_time:.2f} seconds.")
                    time.sleep(sleep_time)
                else:  # Other client-side errors (4xx) are not worth retrying
                    logging.error(f"Request failed with unrecoverable status code {status_code}.")
                    raise e

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exception = e
                sleep_time = backoff_factor * (2 ** attempt)
                logging.warning(f"Network error ({type(e).__name__}) on attempt {attempt + 1}/{max_retries}. Retrying in {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
            
            except ScraperStructureChanged as e:
                # This is a non-recoverable error for this transaction
                logging.error(f"Scraping failed due to HTML structure change: {e}")
                raise e

        # If all retries fail
        logging.error(f"All {max_retries} retries failed.")
        if last_exception:
            raise last_exception
        else:
            # This case should not be reached if there was an error, but as a fallback
            raise Exception("Scraping failed after multiple retries for an unknown reason.")


class PrintArticlesInfo(AbstractTransaction):
    """
    Prints article information to stdout.

    Args:
        data (list): List of article data dictionaries.
        page (int): Current page number.

    Returns:
        None
    """
    def do(self, data, page):
        # Using the csv module would be even better for robust quoting
        for article in data:
            # Properly quote the title to handle commas within it
            print(f"Page {page},{article['id']},\"{article['title']}\",{article['url']}")


def run_instapaper_scraper(session_file=".instapaper_session", key_file=".session_key"):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    session = requests.Session()
    logged_in = False

    # Initialize encryption
    key = get_encryption_key(key_file)
    fernet = Fernet(key)

    # Try to load and decrypt session from file
    if os.path.exists(session_file):
        logging.info(f"Loading encrypted session from {session_file}...")
        try:
            with open(session_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet.decrypt(encrypted_data).decode('utf-8')
            
            for line in decrypted_data.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Expect "name:value:domain"
                parts = line.split(':', 2)
                if len(parts) == 3:
                    name, value, domain = parts
                    session.cookies.set(name, value, domain=domain)
            
            # Verify session after loading all cookies
            if session.cookies:
                verify_response = session.get("https://www.instapaper.com/u")
                if "login_form" not in verify_response.text:
                    logging.info(f"Successfully logged in using the loaded session data.")
                    logged_in = True
        except Exception as e:
            logging.warning(f"Could not load session from {session_file}: {e}. A new session will be created.")
            # If decryption fails, it's safest to delete the corrupt/invalid file
            os.remove(session_file)


    # If not logged in via session file, try .env or prompt for credentials
    if not logged_in:
        logging.info("No valid session found. Please log in.")
        username = os.getenv("INSTAPAPER_USERNAME")
        password = os.getenv("INSTAPAPER_PASSWORD")

        if username and password:
            logging.info(f"Using username '{username}' from environment variables.")
        else:
            username = input("Enter your Instapaper username: ")
            password = getpass.getpass("Enter your Instapaper password: ")
        
        login_response = session.post("https://www.instapaper.com/user/login", data={
            "username": username,
            "password": password,
            "keep_logged_in": "yes"
        })

        # A successful login redirects to the user's article list page ("/u")
        # and sets session cookies.
        required_cookies = ["pfu", "pfp", "pfh"]
        cookies_found = [c for c in session.cookies if c.name in required_cookies]

        if "/u" in login_response.url and cookies_found:
            logging.info("Login successful.")
        else:
            logging.error("Login failed. Please check your credentials.")
            sys.exit(1)


        # Save the session cookies for future runs
        saved_cookie = False
        cookies_found = [c for c in session.cookies if c.name in required_cookies]

        if cookies_found:
            cookie_data = ""
            for cookie in cookies_found:
                cookie_data += f"{cookie.name}:{cookie.value}:{cookie.domain}\n"
            
            encrypted_data = fernet.encrypt(cookie_data.encode('utf-8'))
            
            with open(session_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set file permissions to 0600 (owner read/write only)
            os.chmod(session_file, stat.S_IRUSR | stat.S_IWUSR)
            
            logging.info(f"Saved encrypted session to {session_file}.")
            saved_cookie = True
        
        if not saved_cookie and not logged_in:
            logging.warning("Could not find a known session cookie to save. Scraper will work for this session but not for future ones.")

    # Initialize application with session passed as the "driver"
    app = Application(session)

    print("page,id,title,url")
    page = 1
    has_more = True
    
    try:
        while has_more:
            logging.info(f"Scraping page {page}...")
            ids, data, has_more = app.at(GetArticleIDs, page=page).result
            app.at(PrintArticlesInfo, data=data, page=page)
            page += 1
    except ScraperStructureChanged as e:
        logging.error(f"Stopping scraper due to an unrecoverable error: {e}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logging.error(f"An HTTP error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_instapaper_scraper()
