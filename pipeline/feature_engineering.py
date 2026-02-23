import pandas as pd
from textblob import TextBlob

# --- Sentiment Feature ---
def sentiment_score(text):
    try:
        return TextBlob(text).sentiment.polarity
    except:
        return 0


# --- Clickbait Detection ---
CLICKBAIT_WORDS = [
    "shocking", "breaking", "you won't believe",
    "secret", "exposed", "urgent", "must see"
]

def clickbait_score(title):
    title = str(title).lower()
    return sum(word in title for word in CLICKBAIT_WORDS)


# --- Source Credibility ---
def source_credibility(source):

    if not isinstance(source, str):
        return 0

    source = source.lower()

    TRUSTED_SOURCES = [
        "bbc",
        "reuters",
        "cnn",
        "guardian",
        "ap"
    ]

    return int(any(s in source for s in TRUSTED_SOURCES))


# --- Feature Builder ---
def build_features(df):

    # Ensure required columns exist
    if "source" not in df.columns:
        df["source"] = "unknown"

    df["text_length"] = df["content"].str.len()

    df["sentiment"] = df["content"].apply(sentiment_score)

    df["clickbait_score"] = df["title"].apply(clickbait_score)

    df["source_trust"] = df["source"].apply(source_credibility)

    return df