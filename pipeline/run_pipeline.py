import os
from preprocessing import preprocess_file

RAW_FOLDER = "data/raw"
LOG_FILE = "pipeline/processed_files.log"


def load_processed_files():
    if not os.path.exists(LOG_FILE):
        return set()

    with open(LOG_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_processed_file(filename):
    with open(LOG_FILE, "a") as f:
        f.write(filename + "\n")


def run_pipeline():

    processed_files = load_processed_files()

    new_files_found = False

    for file in os.listdir(RAW_FOLDER):

        if not file.endswith(".csv"):
            continue

        if file in processed_files:
            continue   # skip old files

        print("Processing NEW file:", file)

        preprocess_file(os.path.join(RAW_FOLDER, file))

        save_processed_file(file)

        new_files_found = True

    if not new_files_found:
        print("No new files to process.")


if __name__ == "__main__":
    run_pipeline()