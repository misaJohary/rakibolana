from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup as bs
import unicodedata

app = Flask(__name__)

# Normalize text
def normalize(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").lower()

# Search and parse
def search_malagasy_dictionary(search_term):
    base_url = "http://tenymalagasy.org/bins/teny2"
    response = requests.post(base_url, data={"w": search_term})
    return response.text if response.status_code == 200 else None

def extract_definitions(soup, label_keyword):
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) >= 2 and label_keyword in normalize(tds[0].get_text()):
            raw_html = tds[1].decode_contents().split("<br/>")
            cleaned = []
            for item in raw_html:
                text = bs(item, "html.parser").get_text()
                if "]" in text:
                    text = text.split("]", 1)[-1]
                text = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
                cleaned.append(text.strip())
            return [d for d in cleaned if d]
    return []

def extract_synonyms(soup):
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) >= 2 and "tovy hevitra" in normalize(tds[0].get_text()):
            links = tds[1].find_all("a")
            return [link.get_text(strip=True) for link in links]
    return []

@app.route('/api/teny', methods=['GET'])
def get_word_data():
    search_term = request.args.get('word')
    if not search_term:
        return jsonify({"error": "Missing 'word' parameter"}), 400

    html = search_malagasy_dictionary(search_term)
    if not html:
        return jsonify({"error": "Failed to fetch data"}), 500

    soup = bs(html, 'html.parser')
    word_tag = soup.find("span", class_="entryWord")
    word = word_tag.get_text(strip=True) if word_tag else "unknown"

    word_class = ""
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) >= 2 and "sokajin-teny" in normalize(tds[0].get_text()):
            span = tds[1].find("span", class_="rminute")
            if span:
                span.extract()
            candidate = tds[1].get_text(strip=True)
            if candidate and len(candidate.split()) == 1:
                word_class = candidate
                break

    result = {
        "word": word,
        "class": word_class,
        "definitions": {
            "malagasy": extract_definitions(soup, "teny malagasy"),
            "english": extract_definitions(soup, "teny anglisy"),
            "french": extract_definitions(soup, "teny frantsay")
        },
        "synonyms": extract_synonyms(soup)
    }

    return jsonify(result)

# Optional: homepage
@app.route('/')
def home():
    return "Welcome to the Malagasy Dictionary API. Use /api/teny?word=yourword"

if __name__ == '__main__':
    app.run(debug=True)
