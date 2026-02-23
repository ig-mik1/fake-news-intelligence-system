import json
import os
from datetime import datetime


def save_metrics(acc):

    os.makedirs("models/metrics", exist_ok=True)

    metrics = {
        "accuracy": acc,
        "timestamp": str(datetime.now())
    }

    filename = f"models/metrics/metrics_{datetime.now().timestamp()}.json"

    with open(filename, "w") as f:
        json.dump(metrics, f, indent=4)

    print("Metrics saved:", filename)