# Export Instapaper to HTML

This script allows users to **scrape and download** all saved Instapaper articles as **HTML files** for local storage and offline reading.

## Features
- Scrapes all articles from your Instapaper home page.
- Saves articles in a structured HTML format.
- Logs failed downloads into a `failed.txt` file.
- Truncates filenames to avoid excessively long names.
- Preserves the link to the original page within each article.

## Requirements
Ensure the following Python libraries are installed:
- `requests`
- `beautifulsoup4`

You can install them via pip:

```sh
pip install requests beautifulsoup4
```

## Setup
1. Clone or download the Gist repository.
2. Update the script with your **Instapaper username and password**:
    ```python
    s.post("https://www.instapaper.com/user/login", data={
        "username": "YOUR_USERNAME",
        "password": "YOUR_PASSWORD",
        "keep_logged_in": "yes"
    })
    ```
3. Create an `output` directory where articles will be stored.
4. Run the script:

    ```sh
    python scrape.py
    ```

## How It Works
1. **Authenticate**: Logs into Instapaper using your credentials.
2. **Extract Article IDs**: Fetches article IDs from the home page.
3. **Scrape Content**: Retrieves article title, original link, and formatted content.
4. **Save as HTML**: Stores articles in the `output` directory with a properly formatted filename.
5. **Log Errors**: If any article fails to download, the error is recorded in `failed.txt`.

## Example Output
Each saved article follows the structure:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Article Title</title>
</head>
<body>
    <h1>Article Title</h1>
    <div id="origin">Original Source · Article ID</div>
    <p>Article content...</p>
</body>
</html>
```

## Acknowledgments
This script is **forked and modified** from:
- [Original Gist by jaflo](https://gist.github.com/jaflo/description.md)
- [Forked Gist by domingogallardo](https://gist.github.com/domingogallardo/b6e615fce5f552db6b36261c96bd8d47)

Modifications include:
- Removed PDF conversion.
- Ensured original article links are retained.
- Filenames truncated to a max of 200 characters.

## Disclaimer
This script requires **valid Instapaper credentials**. Be cautious when using personal account information and ensure compliance with Instapaper’s Terms of Service.
