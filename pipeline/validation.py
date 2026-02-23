def validate_data(df):
    df = df.dropna(subset=["title"])

    df = df[df["title"].str.len() > 10]

    return df