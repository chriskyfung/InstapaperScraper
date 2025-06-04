#!/usr/bin/env python
# coding: utf-8

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from guara.transaction import AbstractTransaction, Application

load_dotenv()

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

        if r.status_code != 200:
            print(f"Failed to retrieve page {page}: {r.text}")
            return [], [], False

        articles = soup.find(id="article_list").find_all("article")
        ids = [i["id"].replace("article_", "") for i in articles]

        data = []
        for i in ids:
            article = soup.find(id="article_" + i)
            title = article.find(class_="article_title").getText().strip()
            link = article.find(class_="title_meta").find("a")["href"]
            data.append((i, title, link))

        has_more = soup.find(class_="paginate_older") is not None
        return ids, data, has_more


class PrintArticlesInfo(AbstractTransaction):
    """
    Prints article information to stdout.

    Args:
        data (list): List of (id, title, url) tuples.
        page (int): Current page number.

    Returns:
        None
    """
    def do(self, data, page):
        for article in data:
            print(f"Page {page},{article[0]},\"{article[1]}\",{article[2]}")


def run_instapaper_scraper():
    # Initialize session and login
    session = requests.Session()
    session.post("https://www.instapaper.com/user/login", data={
        "username": os.getenv("INSTAPAPER_USERNAME"),
        "password": os.getenv("INSTAPAPER_PASSWORD"),
        "keep_logged_in": "yes"
    })

    # Initialize application with session passed as the "driver"
    app = Application(session)

    print("page,id,title,url")
    page = 1
    has_more = True

    while has_more:
        ids, data, has_more = app.at(GetArticleIDs, page=page).result
        app.at(PrintArticlesInfo, data=data, page=page)
        page += 1


if __name__ == "__main__":
    run_instapaper_scraper()
