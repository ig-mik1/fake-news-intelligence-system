import pandas as pd
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


def train_model():

    df = pd.read_csv("data/datasets/latest/training_dataset.csv")

    df["content"] = df["content"].fillna("")

    X_train, X_test, y_train, y_test = train_test_split(
        df["content"],
        df.get("label", [0]*len(df)),
        test_size=0.2,
        random_state=42
    )

    vectorizer = TfidfVectorizer(max_features=10000)

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_vec, y_train)

    preds = model.predict(X_test_vec)

    accuracy = accuracy_score(y_test, preds)

    os.makedirs("models", exist_ok=True)

    pickle.dump(model, open("models/model.pkl", "wb"))
    pickle.dump(vectorizer, open("models/vectorizer.pkl", "wb"))

    print("Model trained. Accuracy:", accuracy)

    return accuracy


if __name__ == "__main__":
    train_model()