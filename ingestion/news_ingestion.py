import requests
import pandas as pd
import os
from datetime import datetime

API_KEY = os.getenv("newsAPI")
URL = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=100&apiKey={API_KEY}"

def fetch_news():
    response = requests.get(URL)
    data = response.json()

    articles = []

    for article in data["articles"]:
        articles.append({
            "title": article["title"],
            "content": article["content"],
            "source": article["source"]["name"],
            "published_at": article["publishedAt"]
        })

    df = pd.DataFrame(articles)

    os.makedirs("data/raw", exist_ok=True)

    filename = f"data/raw/news_{datetime.now().date()}.csv"
    df.to_csv(filename, index=False)

    print("Saved:", filename)


if __name__ == "__main__":
    fetch_news()