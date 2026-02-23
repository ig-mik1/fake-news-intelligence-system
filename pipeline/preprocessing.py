import pandas as pd
import os
from cleaning import clean_dataframe
from validation import validate_data


def preprocess_file(file_path):

    df = pd.read_csv(file_path)

    df = validate_data(df)
    df = clean_dataframe(df)

    os.makedirs("data/processed", exist_ok=True)

    output_path = file_path.replace("raw", "processed")

    df.to_csv(output_path, index=False)

    print("Processed:", output_path)