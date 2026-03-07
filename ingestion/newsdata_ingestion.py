from newsdataapi import NewsDataApiClient
import os
from dotenv import load_dotenv

load_dotenv()   

api = NewsDataApiClient(apikey=os.getenv("NEWSDATA_API_KEY"))

def fetch_enriched_news(query="latest news", country="in"):
    """Fetches news and ensures it has the fields needed for the Datalake."""
    try:
        response = api.latest_api(q=query, country=country, language="en")
        if response['status'] == "success":
            articles = []
            for art in response['results']:
                articles.append({
                    "title": art.get("title", ""),
                    "content": art.get("description") or art.get("content") or "",
                    "url": art.get("link", ""),
                    "source": art.get("source_id", "Unknown"),
                    "sentiment": art.get("sentiment", "neutral")
                })
            return articles
    except Exception as e:
        print(f"NewsData Error: {e}")
    return []