#!/usr/bin/env python
# coding: utf-8

import requests
from bs4 import BeautifulSoup
import os

from dotenv import load_dotenv
load_dotenv()

s = requests.Session()
s.post("https://www.instapaper.com/user/login", data={
    "username": os.getenv("INSTAPAPER_USERNAME"),
    "password": os.getenv("INSTAPAPER_PASSWORD"),
    "keep_logged_in": "yes"
})
base = "./output/"

def get_ids(page=1):
    enable_folder_mode = os.getenv("ENABLE_FOLDER_MODE", False).lower() in ("true", "1", "t")
    folder_id_and_slug = os.getenv("FOLDER_ID_AND_SLUG")

    if enable_folder_mode:
        url = f"https://www.instapaper.com/u/folder/{folder_id_and_slug}/{page}"
    else:
        # Default to the user's main page
        # This will get all articles, not just those in a specific folder
        url = f"https://www.instapaper.com/u/{page}"
    r = s.get(url)
    
    if r.status_code != 200:
        print(f"Failed to retrieve page {page}: {r.text}")
        return [], [], False

    soup = BeautifulSoup(r.text, "html.parser")

    articles = soup.find(id="article_list").find_all("article")
    ids = [i["id"].replace("article_", "") for i in articles]
    data = []
    for i in ids:
        article = soup.find(id="article_" + i)
        title = article.find(class_="article_title").getText().strip()
        url = article.find(class_="title_meta").find("a")["href"]
        data.append((i, title, url))
    has_more = soup.find(class_="paginate_older") is not None
    return ids, data, has_more

def print_article_info(data, page):
    for i in data:
      print("Page " + str(page) + ',' + i[0] + ',"' + i[1] + '",' + i[2])

has_more = True
page = 1

failure_log = open("failed.txt", "a+")

print("page,id,title,url")
while has_more:
    ids, data, has_more = get_ids(page)
    print_article_info(data, page)
    page += 1
