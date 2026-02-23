import os
import pandas as pd
from datetime import datetime

from gnews_api import fetch_gnews
from rss_ingestion import fetch_rss

# Reddit is OPTIONAL
try:
    from reddit_ingestion import fetch_reddit
    REDDIT_AVAILABLE = True
except Exception:
    REDDIT_AVAILABLE = False


def run_all():

    dfs = []

    print("Starting ingestion pipeline...\n")

    # -------- GNews --------
    try:
        print("Fetching GNews...")
        dfs.append(fetch_gnews())
    except Exception as e:
        print("GNews failed:", e)

    # -------- RSS --------
    try:
        print("Fetching RSS feeds...")
        dfs.append(fetch_rss())
    except Exception as e:
        print("RSS failed:", e)

    # -------- Reddit (Optional) --------
    if REDDIT_AVAILABLE:
        try:
            print("Fetching Reddit...")
            dfs.append(fetch_reddit())
        except Exception as e:
            print("Reddit skipped:", e)
    else:
        print("Reddit module not available — skipping.")

    if not dfs:
        print("No data collected.")
        return

    final_df = pd.concat(dfs, ignore_index=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs("data/raw", exist_ok=True)

    filename = f"data/raw/combined_{timestamp}.csv"

    final_df.to_csv(filename, index=False)

    print("\nSaved:", filename)
    print("Records collected:", len(final_df))


if __name__ == "__main__":
    run_all()