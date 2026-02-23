import os
import pandas as pd

RAW_FOLDER = "data/raw"


def load_recent_news():

    all_news = []

    if not os.path.exists(RAW_FOLDER):
        return pd.DataFrame()

    for file in os.listdir(RAW_FOLDER):
        if file.endswith(".csv"):
            df = pd.read_csv(os.path.join(RAW_FOLDER, file))
            all_news.append(df)

    if not all_news:
        return pd.DataFrame()

    return pd.concat(all_news, ignore_index=True)


def compute_monitoring_stats(df):

    if df.empty:
        return {}

    total_articles = len(df)

    sources = df["source"].value_counts().head(5).to_dict()

    avg_length = df["content"].astype(str).apply(len).mean()

    return {
        "total_articles": total_articles,
        "top_sources": sources,
        "avg_length": round(avg_length, 2),
    }