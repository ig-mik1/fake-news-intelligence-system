import pandas as pd

fake = pd.read_csv("data/seed/Fake.csv")
real = pd.read_csv("data/seed/True.csv")

fake["label"] = 1
real["label"] = 0

df = pd.concat([fake, real])

df = df[["title", "text", "label"]]

df.rename(columns={"text": "content"}, inplace=True)

df.to_csv("data/seed/fake_news_dataset.csv", index=False)

print("ISOT dataset prepared.")