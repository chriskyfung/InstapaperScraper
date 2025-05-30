#!/usr/bin/env python
import requests
import os
# import pdfkit
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict
from dotenv import load_dotenv
from guara.transaction import AbstractTransaction, Application
from guara import it

load_dotenv()

# ----------------------
# Concrete Transactions
# ----------------------
class Login(AbstractTransaction):
    def do(self, **kwargs):
        response = self._driver.post(
            "https://www.instapaper.com/user/login",
            data={
                "username": os.getenv("INSTAPAPER_USERNAME"),
                "password": os.getenv("INSTAPAPER_PASSWORD"),
                "keep_logged_in": "yes"
            }
        )
        return response.status_code == 200

class GetArticleIDs(AbstractTransaction):
    def do(self, page: int = 1, **kwargs) -> Tuple[List[str], List[Tuple[str, str, str]], bool]:
        enable_folder_mode = os.getenv("ENABLE_FOLDER_MODE", False)
        folder_id_and_slug = os.getenv("FOLDER_ID_AND_SLUG")

        if enable_folder_mode:
            url = f"https://www.instapaper.com/u/folder/{folder_id_and_slug}/{page}"
        else:
            url = f"https://www.instapaper.com/u/{page}"

        response = self._driver.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.find(id="article_list").find_all("article")
        ids = [i["id"].replace("article_", "") for i in articles]
        
        data = []
        for article_id in ids:
            article = soup.find(id=f"article_{article_id}")
            title = article.find(class_="article_title").getText().strip()
            url = article.find(class_="title_meta").find("a")["href"]
            data.append((article_id, title, url))
        
        has_more = soup.find(class_="paginate_older") is not None
        return ids, data, has_more

class GetArticleContent(AbstractTransaction):
    def do(self, article_id: str, **kwargs) -> Dict[str, str]:
        response = self._driver.get(f"https://www.instapaper.com/read/{article_id}")
        soup = BeautifulSoup(response.text, "html.parser")

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

class SaveArticleAsHTML(AbstractTransaction):
    def do(self, article_id: str, content: Dict[str, str], output_dir: str = "./output/", **kwargs) -> str:
        file_name = f"{article_id} {content['title']}"
        file_name = "".join([c for c in file_name if c.isalpha() or c.isdigit() or c == " "]).rstrip()
        file_name = os.path.join(output_dir, file_name + ".html")

        with open(file_name, "w", encoding="utf-8") as file:
            file.write(f"<h1>{content['title']}</h1>")
            file.write(f"<div id='origin'>{content['origin']} · {article_id}</div>")
            file.write(content["content"])
        
        return file_name

class ConvertToPDF(AbstractTransaction):
    def do(self, html_file: str, **kwargs) -> str:
        pdf_file = html_file[:-5] + ".pdf"
        options = {
            "page-size": "Letter",
            "margin-top": "0.75in",
            "margin-right": "0.75in",
            "margin-bottom": "0.75in",
            "margin-left": "0.75in",
            "encoding": "UTF-8",
            "no-outline": None,
            "user-style-sheet": "styles.css",
            "load-error-handling": "ignore",
            "quiet": "",
        }
        # pdfkit.from_file(html_file, pdf_file, options=options)
        return pdf_file

# ----------------------
# Test Function
# ----------------------
def test_sample():
    session = requests.Session()
    app = Application(session)
    output_dir = "./output/"
    os.makedirs(output_dir, exist_ok=True)

    # Login and verify
    app.at(Login).asserts(it.IsEqualTo, True)

    print("page,id,title,url")
    
    # Process first 2 pages as a sample
    for page in range(1, 3):
        ids, data, has_more = app.at(GetArticleIDs, page=page).result
        app.asserts(it.IsEqualTo, len(ids) > 0, True)  # Verify we got articles
        
        for article_id, title, url in data:
            print(f"{page},{article_id},{title},{url}")
            
            try:
                content = app.at(GetArticleContent, article_id=article_id).result
                html_file = app.at(
                    SaveArticleAsHTML, 
                    article_id=article_id,
                    content=content,
                    output_dir=output_dir
                ).result
                pdf_file = app.at(ConvertToPDF, html_file=html_file).result
                print(f"Created: {pdf_file}")
            except Exception as e:
                print(f"Error processing {article_id}: {str(e)}")
        
        if not has_more:
            break

if __name__ == "__main__":
    test_sample()