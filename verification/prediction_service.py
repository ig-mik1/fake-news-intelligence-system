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


def _resolve_label_index(model, target: str) -> Optional[int]:
    id2label = getattr(model.config, "id2label", {}) or {}
    target_upper = target.upper()
    for idx, raw_name in id2label.items():
        name = str(raw_name).upper()
        if name == target_upper:
            return int(idx)
        if target_upper == "FAKE" and "FAKE" in name:
            return int(idx)
        if target_upper == "REAL" and ("REAL" in name or "TRUE" in name):
            return int(idx)
    return None


def _extract_binary_probabilities(model, probs_tensor) -> Tuple[float, float]:
    probs = [float(x) for x in probs_tensor[0].tolist()]
    fake_idx = _resolve_label_index(model, "FAKE")
    real_idx = _resolve_label_index(model, "REAL")

    if fake_idx is None and len(probs) > 1:
        fake_idx = 1
    if real_idx is None and len(probs) > 0:
        real_idx = 0

    fake_prob = probs[fake_idx] if fake_idx is not None and fake_idx < len(probs) else 0.0
    real_prob = probs[real_idx] if real_idx is not None and real_idx < len(probs) else 0.0

    total = fake_prob + real_prob
    if total > 0:
        fake_prob /= total
        real_prob /= total
    elif len(probs) >= 2:
        fake_prob = probs[1]
        real_prob = probs[0]
    else:
        fake_prob = 0.5
        real_prob = 0.5

    return real_prob, fake_prob


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
    real_prob, fake_prob = _extract_binary_probabilities(model, probs)
    predicted_label = "FAKE" if fake_prob >= real_prob else "REAL"
    predicted_confidence = fake_prob if predicted_label == "FAKE" else real_prob

    return {
        "label": predicted_label,
        "confidence": round(float(predicted_confidence) * 100, 2),
        "ml_fake_probability": round(float(fake_prob), 6),
        "ml_real_probability": round(float(real_prob), 6),
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
