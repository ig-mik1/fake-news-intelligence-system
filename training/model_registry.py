import shutil
import os

def register_model():

    os.makedirs("models/registry", exist_ok=True)

    version = len(os.listdir("models/registry")) + 1

    shutil.copy("models/model.pkl",
                f"models/registry/model_v{version}.pkl")

    print(f"Registered Model v{version}")