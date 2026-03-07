import inspect
import math
import os
from typing import Any, Dict, List

import torch
from datasets import Dataset, DatasetDict, load_from_disk
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

# 1) Imports and global config
MODEL_NAME = "distilroberta-base"
DATASET_PATH = "data/processed/hf_dataset"
CHECKPOINT_DIR = "./models/checkpoints"
FINAL_MODEL_DIR = "models/final_model"
SEED = 42
MAX_LENGTH = 192
MAX_CONTENT_WORDS = 150
TRAIN_BATCH_SIZE = 4
EVAL_BATCH_SIZE = 4
GRAD_ACCUMULATION_STEPS = 4
NUM_EPOCHS = 2
TOKENIZATION_KWARGS = {
    "truncation": True,
    "max_length": MAX_LENGTH,
}


# 2) Dataset/text helpers
def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _clip_to_words(text: str, limit: int) -> str:
    words = _clean_text(text).split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit])


def build_tokenize_function(tokenizer):
    # 5) Tokenization function (paired title + clipped content)
    def tokenize_function(examples: Dict[str, List[Any]]) -> Dict[str, Any]:
        titles = [_clean_text(value) for value in examples.get("title", [])]
        raw_contents = examples.get("content", [""] * len(titles))
        contents = [_clip_to_words(value, MAX_CONTENT_WORDS) for value in raw_contents]

        if len(contents) != len(titles):
            contents = [""] * len(titles)

        return tokenizer(
            titles,
            text_pair=contents,
            **TOKENIZATION_KWARGS,
        )

    return tokenize_function


def compute_metrics(pred) -> Dict[str, float]:
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        preds,
        average="binary",
        zero_division=0,
    )
    acc = accuracy_score(labels, preds)
    return {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def _ensure_dataset_splits(dataset_obj: Any) -> DatasetDict:
    # 3) Dataset split
    if isinstance(dataset_obj, DatasetDict):
        if "train" in dataset_obj and "test" in dataset_obj:
            return dataset_obj
        first_key = next(iter(dataset_obj.keys()))
        return dataset_obj[first_key].train_test_split(test_size=0.1, seed=SEED)

    if isinstance(dataset_obj, Dataset):
        return dataset_obj.train_test_split(test_size=0.1, seed=SEED)

    raise TypeError(f"Unsupported dataset type: {type(dataset_obj)!r}")


def _build_training_args(train_rows: int) -> TrainingArguments:
    # 9) Training arguments (optimized for GTX 1650 4GB)
    # total optimizer update steps across all epochs
    total_update_steps = math.ceil(
        max(1, train_rows) / (TRAIN_BATCH_SIZE * GRAD_ACCUMULATION_STEPS)
    ) * NUM_EPOCHS
    warmup_steps = max(1, int(total_update_steps * 0.05))

    kwargs: Dict[str, Any] = {
        "output_dir": CHECKPOINT_DIR,
        "save_strategy": "epoch",
        "learning_rate": 3e-5,
        "weight_decay": 0.01,
        "warmup_steps": warmup_steps,
        "per_device_train_batch_size": TRAIN_BATCH_SIZE,
        "per_device_eval_batch_size": EVAL_BATCH_SIZE,
        "gradient_accumulation_steps": GRAD_ACCUMULATION_STEPS,
        "num_train_epochs": NUM_EPOCHS,
        "fp16": torch.cuda.is_available(),
        "dataloader_num_workers": min(2, os.cpu_count() or 1),
        "dataloader_pin_memory": torch.cuda.is_available(),
        "remove_unused_columns": False,
        "max_grad_norm": 1.0,
        "logging_steps": 100,
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1",
        "greater_is_better": True,
        "report_to": "none",
        "seed": SEED,
    }

    ta_params = inspect.signature(TrainingArguments.__init__).parameters
    if "evaluation_strategy" in ta_params:
        kwargs["evaluation_strategy"] = "epoch"
    else:
        kwargs["eval_strategy"] = "epoch"

    return TrainingArguments(**kwargs)


def _build_trainer(
    model,
    training_args: TrainingArguments,
    train_dataset,
    eval_dataset,
    tokenizer,
    data_collator,
) -> Trainer:
    # 10) Trainer initialization with version-safe tokenizer argument
    trainer_kwargs: Dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "data_collator": data_collator,
        "compute_metrics": compute_metrics,
    }
    trainer_params = inspect.signature(Trainer.__init__).parameters
    if "tokenizer" in trainer_params:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in trainer_params:
        trainer_kwargs["processing_class"] = tokenizer

    return Trainer(**trainer_kwargs)


def train():
    # 2) Dataset loading
    print("Loading preprocessed dataset...")
    dataset_obj = load_from_disk(DATASET_PATH)

    # 3) Dataset split
    dataset = _ensure_dataset_splits(dataset_obj)

    # 4) Tokenizer setup
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

    # 6) dataset.map tokenization (batched, no static padding)
    print("Tokenizing with paired inputs: title + clipped content")
    tokenized_datasets = dataset.map(
        build_tokenize_function(tokenizer),
        batched=True,
    )

    columns_to_remove = [
        col
        for col in tokenized_datasets["train"].column_names
        if col not in {"input_ids", "attention_mask", "token_type_ids", "label"}
    ]
    if columns_to_remove:
        tokenized_datasets = tokenized_datasets.remove_columns(columns_to_remove)

    # 7) Dynamic padding collator + tensor format
    tokenized_datasets["train"] = tokenized_datasets["train"].shuffle(seed=SEED)
    tokenized_datasets.set_format("torch")
    data_collator = DataCollatorWithPadding(
        tokenizer=tokenizer,
        pad_to_multiple_of=8 if torch.cuda.is_available() else None,
    )

    # 8) Model init
    print("Loading model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"Using device: {device}")

    # 9) Training args
    training_args = _build_training_args(train_rows=len(tokenized_datasets["train"]))

    # 10) Trainer init
    trainer = _build_trainer(
        model=model,
        training_args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # 11) Train
    print("Starting FNIS model training...")
    trainer.train()

    # 12) Evaluate
    metrics = trainer.evaluate()
    print("Validation metrics:", metrics)

    # 13) Save model
    print(f"Saving best model to {FINAL_MODEL_DIR} ...")
    trainer.save_model(FINAL_MODEL_DIR)
    tokenizer.save_pretrained(FINAL_MODEL_DIR)
    print("Training complete.")


if __name__ == "__main__":
    train()
