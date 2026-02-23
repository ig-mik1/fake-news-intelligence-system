import os
import pandas as pd


RAW_FOLDER = "data/raw"


def consensus_score(text):

    matches = 0
    total_files = 0

    for file in os.listdir(RAW_FOLDER):

        if not file.endswith(".csv"):
            continue

        df = pd.read_csv(os.path.join(RAW_FOLDER, file))

        total_files += 1

        if df["content"].str.contains(text[:40], case=False).any():
            matches += 1

    if total_files == 0:
        return 0.5

    return matches / total_files