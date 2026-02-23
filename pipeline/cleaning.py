import pandas as pd
import re

def clean_text(text):
    if pd.isna(text):
        return ""

    text = re.sub(r"http\S+", "", text)      # remove links
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    text = text.lower()
    text = text.strip()

    return text


def clean_dataframe(df):
    df["title"] = df["title"].apply(clean_text)
    df["content"] = df["content"].apply(clean_text)

    df.drop_duplicates(subset=["title"], inplace=True)

    return df