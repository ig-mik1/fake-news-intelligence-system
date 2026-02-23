from train import train_model
from evaluate import save_metrics
from model_registry import register_model


def run_retraining():

    print("Starting MLOps Pipeline...")

    acc = train_model()

    save_metrics(acc)

    register_model()

    print("Pipeline Complete!")


if __name__ == "__main__":
    run_retraining()