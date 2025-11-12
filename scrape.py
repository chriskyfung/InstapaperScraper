#!/usr/bin/env python
# coding: utf-8

import os
import requests
import sys
import logging
import getpass
import stat
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from guara.transaction import AbstractTransaction, Application
from cryptography.fernet import Fernet

load_dotenv()

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

        r = self._driver.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        r.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)

        article_list = soup.find(id="article_list")
        articles = article_list.find_all("article") if article_list else []
        ids = [i["id"].replace("article_", "") for i in articles]

        data = []
        for i in ids:
            article = soup.find(id="article_" + i)
            title = article.find(class_="article_title").getText().strip()
            link = article.find(class_="title_meta").find("a")["href"]
            data.append({
                "id": i,
                "title": title,
                "url": link
            })

        has_more = soup.find(class_="paginate_older") is not None
        return ids, data, has_more


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
    except requests.exceptions.RequestException as e:
        logging.error(f"An HTTP error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_instapaper_scraper()
