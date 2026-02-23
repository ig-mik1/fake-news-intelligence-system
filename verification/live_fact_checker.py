import requests
import os
from dotenv import load_dotenv

load_dotenv()
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")


def search_live_news(query, max_results=5):

    url = "https://gnews.io/api/v4/search"

    params = {
        "q": query,
        "lang": "en",
        "max": max_results,
        "apikey": GNEWS_API_KEY,
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        articles = []

        for article in data.get("articles", []):
            articles.append({
                "title": article["title"],
                "source": article["source"]["name"],
                "url": article["url"]
            })

        return articles

    except Exception:
        return []