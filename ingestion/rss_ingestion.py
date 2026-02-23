import feedparser
import pandas as pd

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "http://rss.cnn.com/rss/edition.rss",
    "https://feeds.reuters.com/reuters/topNews"
]


def extract_content(entry):

    # Try multiple fields safely
    if hasattr(entry, "summary"):
        return entry.summary

    if hasattr(entry, "description"):
        return entry.description

    if hasattr(entry, "content"):
        return entry.content[0].value

    return ""


def fetch_rss():

    articles = []

    for feed in RSS_FEEDS:

        parsed = feedparser.parse(feed)

        for entry in parsed.entries:

            articles.append({
                "title": getattr(entry, "title", ""),
                "content": extract_content(entry),
                "source": feed,
                "platform": "rss"
            })

    return pd.DataFrame(articles)