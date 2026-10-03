from __future__ import annotations

import importlib
from typing import Any

from .models import Stance


_LABEL_TO_STANCE = {
    "entailment": Stance.SUPPORTS,
    "contradiction": Stance.CONTRADICTS,
    "neutral": Stance.NEUTRAL,
}


def _resolve_label_map(id2label: dict[int, str]) -> dict[int, Stance]:
    normalized = {index: label.strip().casefold() for index, label in id2label.items()}
    if set(normalized.values()) != set(_LABEL_TO_STANCE):
        raise ValueError(
            "NLI model must expose exactly entailment, contradiction and neutral labels"
        )
    return {index: _LABEL_TO_STANCE[label] for index, label in normalized.items()}


class TransformersNLIBackend:
    """CPU-only three-class NLI backend with an explicit label-map contract."""

    def __init__(self, model_id: str, model_revision: str) -> None:
        if not model_id.strip() or not model_revision.strip():
            raise ValueError("model_id and model_revision are required")
        self.model_id = model_id
        self.model_revision = model_revision
        self._label_map: dict[int, Stance] | None = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._torch: Any = None

    def _load(self) -> dict[int, Stance]:
        if self._label_map is not None:
            return self._label_map

        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'nli' extra to use TransformersNLIBackend"
            ) from exc

        tokenizer = transformers.AutoTokenizer.from_pretrained(
            self.model_id,
            revision=self.model_revision,
        )
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            self.model_id,
            revision=self.model_revision,
        )
        model.eval()
        label_map = _resolve_label_map(
            {int(index): str(label) for index, label in model.config.id2label.items()}
        )
        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._label_map = label_map
        return label_map

    def classify(self, claim_text: str, evidence_text: str) -> dict[str, float | str]:
        label_map = self._load()
        encoded = self._tokenizer(
            claim_text,
            evidence_text,
            return_tensors="pt",
            truncation=True,
        )
        with self._torch.inference_mode():
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1)
        index = int(self._torch.argmax(probabilities).item())
        return {
            "stance": label_map[index].value,
            "confidence": float(probabilities[index].item()),
        }
