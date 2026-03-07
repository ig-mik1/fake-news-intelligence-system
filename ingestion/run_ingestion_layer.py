import hashlib
from datetime import datetime, timezone

import chromadb
import pandas as pd

try:
    from ingestion.newsdata_ingestion import fetch_enriched_news
    from ingestion.reddit_ingestion import fetch_reddit_evidence
    from ingestion.rss_ingestion import fetch_rss
except ModuleNotFoundError:
    # Allows direct execution: `python ingestion/run_ingestion_layer.py`
    from newsdata_ingestion import fetch_enriched_news
    from reddit_ingestion import fetch_reddit_evidence
    from rss_ingestion import fetch_rss


client = chromadb.PersistentClient(path="./data/vector_storage")
collection = client.get_or_create_collection(name="news_evidence")


def get_unique_id(url):
    """Generate a deterministic ID from URL."""
    if not url:
        url = str(hash(url))
    return hashlib.md5(url.encode()).hexdigest()


def run_master_ingestion(query="latest news"):
    print(f"Starting ingestion for: {query}")

    rss_df = fetch_rss()
    news_data = fetch_enriched_news(query)
    reddit_data = fetch_reddit_evidence(query)

    master_list = []

    if isinstance(rss_df, pd.DataFrame):
        for _, row in rss_df.iterrows():
            master_list.append(
                {
                    "id": get_unique_id(row.get("url", "")),
                    "title": row.get("title", ""),
                    "content": row.get("content", ""),
                    "url": row.get("url", ""),
                    "source": row.get("source", "rss"),
                    "platform": "rss",
                }
            )

    for art in news_data:
        master_list.append(
            {
                "id": get_unique_id(art.get("url", "")),
                "title": art.get("title", ""),
                "content": art.get("content", ""),
                "url": art.get("url", ""),
                "source": art.get("source", "newsapi"),
                "platform": "newsdata",
                "sentiment": art.get("sentiment"),
            }
        )

    for post in reddit_data:
        master_list.append(
            {
                "id": get_unique_id(post.get("url", "")),
                "title": post.get("title", ""),
                "content": post.get("text", ""),
                "url": post.get("url", ""),
                "source": post.get("source", "reddit"),
                "platform": "reddit",
            }
        )

    if not master_list:
        print("No items fetched from any source. Nothing to ingest.")
        return

    # Remove duplicate IDs across sources
    unique_items = {}
    for item in master_list:
        unique_items[item["id"]] = item
    master_list = list(unique_items.values())

    # Get already stored IDs
    existing_resp = collection.get(include=[])
    existing_ids = existing_resp.get("ids", []) if isinstance(existing_resp, dict) else []
    existing = set(existing_ids or [])
    new_items = []
    for item in master_list:
        if item["id"] not in existing:
            new_items.append(item)

    if not new_items:
        print("No new articles to ingest.")
        return

    documents = [f"{item['title']} {item['content']}".strip() for item in new_items]
    ids = [item["id"] for item in new_items]
    metadatas = [
        {
            "title": item["title"],
            "url": item["url"],
            "source": item["source"],
            "platform": item["platform"],
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        for item in new_items
    ]

    collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    print(f"Ingestion complete. {len(new_items)} new items processed.")


if __name__ == "__main__":
    run_master_ingestion()
