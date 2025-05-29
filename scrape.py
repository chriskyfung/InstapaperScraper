#!/usr/bin/env python
# coding: utf-8

import requests
import time
from bs4 import BeautifulSoup
import pdfkit
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
    r = s.get("https://www.instapaper.com/u/" + str(page))
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


def get_article(id):
    r = s.get("https://www.instapaper.com/read/" + str(id))
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find(id="titlebar").find("h1").getText()
    origin = soup.find(id="titlebar").find(class_="origin_line").getText()
    url = soup.find(id="titlebar").find("a")["href"]
    content = soup.find(id="story").decode_contents()
    return {
        "title": title.strip(),
        "origin": origin.strip(),
        "url": url.strip(),
        "content": content.strip()
    }


def article_converted(id):
    for file_name in os.listdir(base):
        if file_name.startswith(id) and file_name.endswith(".pdf"):
            return base + os.path.basename(file_name)
    return None

def print_article_info(data, page):
    for i in data:
      print("Page " + str(page) + ',' + i[0] + ',"' + i[1] + '",' + i[2])

def download_article(id):
    article = get_article(id)
    file_name = id + " " + article["title"]
    file_name = "".join([c for c in file_name if c.isalpha()
                         or c.isdigit() or c == " "]).rstrip()
    file_name = base + file_name + ".html"

    with open(file_name, "w") as file:
        file.write("<h1>%s</h1>" % (article["title"]))
        file.write("<div id='origin'>%s · %s</div>" % (article["origin"], id))
        file.write(article["content"])

    return file_name


def convert_to_pdf(file_name):
    new_name = file_name[:-5] + ".pdf"
    margin = "0.75in"
    options = {
        "page-size": "Letter",
        "margin-top": margin,
        "margin-right": margin,
        "margin-bottom": margin,
        "margin-left": margin,
        "encoding": "UTF-8",
        "no-outline": None,
        "user-style-sheet": "styles.css",
        "load-error-handling": "ignore",
        "quiet": "",
    }

    pdfkit.from_file(file_name, new_name, options=options)
    return new_name


has_more = True
page = 1

failure_log = open("failed.txt", "a+")

print("page,id,title,url")
while has_more:
    ids, data, has_more = get_ids(page)
    print_article_info(data, page)
    page += 1
