import os
import pandas as pd

RAW_FOLDER = "data/raw"


def find_evidence(query_text, top_k=5):

    evidence = []

    if not os.path.exists(RAW_FOLDER):
        return evidence

    query_words = query_text.lower().split()[:6]

    for file in os.listdir(RAW_FOLDER):

        if not file.endswith(".csv"):
            continue

        df = pd.read_csv(os.path.join(RAW_FOLDER, file))

        for _, row in df.iterrows():

            content = str(row.get("content", "")).lower()

            score = sum(word in content for word in query_words)

            if score >= 2:
                evidence.append({
                    "title": row.get("title", ""),
                    "source": row.get("source", "Unknown"),
                    "url": row.get("url", "")
                })

    return evidence[:top_k]