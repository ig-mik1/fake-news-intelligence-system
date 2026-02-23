import pandas as pd
import os
from datetime import datetime
from feature_engineering import build_features

PROCESSED_FOLDER = "data/processed"
SEED_DATASET = "data/seed/fake_news_dataset.csv"


def load_processed_data():

    dfs = []

    if not os.path.exists(PROCESSED_FOLDER):
        return dfs

    for file in os.listdir(PROCESSED_FOLDER):
        if file.endswith(".csv"):
            path = os.path.join(PROCESSED_FOLDER, file)
            df = pd.read_csv(path)

            # Live news assumed REAL
            df["label"] = 0

            dfs.append(df)

    return dfs


def load_seed_dataset():

    if not os.path.exists(SEED_DATASET):
        print("Seed dataset not found.")
        return []

    print("Loading seed dataset...")
    seed_df = pd.read_csv(SEED_DATASET)

    return [seed_df]


def build_training_dataset():

    all_dfs = []

    print("Loading processed live data...")
    all_dfs.extend(load_processed_data())

    print("Loading curated seed dataset...")
    all_dfs.extend(load_seed_dataset())

    if not all_dfs:
        print("No data available!")
        return

    combined = pd.concat(all_dfs, ignore_index=True)

    combined = build_features(combined)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs("data/datasets/versions", exist_ok=True)

    version_path = f"data/datasets/versions/training_{timestamp}.csv"
    combined.to_csv(version_path, index=False)

    os.makedirs("data/datasets/latest", exist_ok=True)

    latest_path = "data/datasets/latest/training_dataset.csv"
    combined.to_csv(latest_path, index=False)

    print("\nSaved version:", version_path)
    print("Updated latest dataset")

    print("\nLabel Distribution:")
    print(combined["label"].value_counts())


if __name__ == "__main__":
    build_training_dataset()