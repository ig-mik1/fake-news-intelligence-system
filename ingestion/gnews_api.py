import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GNEWS_API_KEY")

def fetch_gnews():
    url = f"https://gnews.io/api/v4/top-headlines?lang=en&max=100&token={API_KEY}"
    r = requests.get(url)
    data = r.json()

    articles = []

    for a in data["articles"]:
        articles.append({
            "title": a["title"],
            "content": a["description"],
            "source": a["source"]["name"],
            "platform": "gnews"
        })

    return pd.DataFrame(articles)