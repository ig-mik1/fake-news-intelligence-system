import logging
import os
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

LOGGER = logging.getLogger(__name__)

MODEL_PATH = os.getenv("FNIS_MODEL_PATH", "models/final_model")
MAX_LENGTH = int(os.getenv("FNIS_MAX_LENGTH", "192"))
MAX_INPUT_CHARS = int(os.getenv("FNIS_MAX_INPUT_CHARS", "4000"))
TOKENIZATION_KWARGS = {
    "truncation": True,
    "padding": "max_length",
    "max_length": MAX_LENGTH,
}

_LOAD_LOCK = Lock()
_TOKENIZER = None
_MODEL = None
_DEVICE = None


def _resolve_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model_artifacts() -> Tuple[Any, Any, torch.device]:
    global _TOKENIZER, _MODEL, _DEVICE

    if _TOKENIZER is not None and _MODEL is not None and _DEVICE is not None:
        return _TOKENIZER, _MODEL, _DEVICE

    with _LOAD_LOCK:
        if _TOKENIZER is not None and _MODEL is not None and _DEVICE is not None:
            return _TOKENIZER, _MODEL, _DEVICE

        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(f"Model path not found: {MODEL_PATH}")

        LOGGER.info("Loading prediction model from %s", MODEL_PATH)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

        device = _resolve_device()
        model.to(device)
        model.eval()

        _TOKENIZER = tokenizer
        _MODEL = model
        _DEVICE = device

    return _TOKENIZER, _MODEL, _DEVICE


def _normalize_label(label: str) -> str:
    upper = str(label).upper()
    if upper in {"LABEL_0", "REAL"}:
        return "REAL"
    if upper in {"LABEL_1", "FAKE"}:
        return "FAKE"
    return upper


def _validate_text(text: Any) -> str:
    if not isinstance(text, str):
        raise ValueError("Input text must be a string.")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Input text cannot be empty.")

    if len(cleaned) > MAX_INPUT_CHARS:
        cleaned = cleaned[:MAX_INPUT_CHARS]

    return cleaned


def _validate_optional_content(content: Any) -> str:
    if content is None:
        return ""
    if not isinstance(content, str):
        raise ValueError("Input content must be a string when provided.")

    cleaned = content.strip()
    if len(cleaned) > MAX_INPUT_CHARS:
        cleaned = cleaned[:MAX_INPUT_CHARS]
    return cleaned


def predict_fake_news(text: str, content: Optional[str] = None) -> Dict[str, Any]:
    cleaned_text = _validate_text(text)
    cleaned_content = _validate_optional_content(content)
    tokenizer, model, device = _load_model_artifacts()

    if cleaned_content:
        inputs = tokenizer(
            cleaned_text,
            text_pair=cleaned_content,
            return_tensors="pt",
            **TOKENIZATION_KWARGS,
        )
    else:
        inputs = tokenizer(
            cleaned_text,
            return_tensors="pt",
            **TOKENIZATION_KWARGS,
        )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    confidence, label_idx = torch.max(probs, dim=1)
    idx = int(label_idx.item())

    id2label = getattr(model.config, "id2label", {}) or {}
    raw_label = id2label.get(idx, "FAKE" if idx == 1 else "REAL")

    return {
        "label": _normalize_label(raw_label),
        "confidence": round(float(confidence.item()) * 100, 2),
        "raw_scores": [float(x) for x in probs[0].tolist()],
        "uses_content": bool(cleaned_content),
        "device": str(device),
        "model_path": MODEL_PATH,
    }


def get_model_status() -> Dict[str, Any]:
    path_exists = os.path.exists(MODEL_PATH)
    status: Dict[str, Any] = {
        "path": MODEL_PATH,
        "path_exists": path_exists,
        "loaded": False,
        "device": None,
    }

    if not path_exists:
        status["error"] = "Model path not found."
        return status

    try:
        _, _, device = _load_model_artifacts()
        status["loaded"] = True
        status["device"] = str(device)
    except Exception as exc:
        status["error"] = str(exc)

    return status


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_text = "ISRO successfully launches 500 satellites in a single day"
    print(predict_fake_news(test_text))
