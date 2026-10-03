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

    model_revision: str

    def __post_init__(self) -> None:
        if not self.model_revision.strip():
            raise ValueError("model_revision is required")
        object.__setattr__(self, "_pipeline", None)
        object.__setattr__(self, "_label_map", None)

    def _load(self) -> tuple[Any, dict[int, Stance]]:
        pipeline = self._pipeline
        label_map = self._label_map
        if pipeline is not None and label_map is not None:
            return pipeline, label_map

        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'nli' extra to use TransformersNLIBackend"
            ) from exc

        tokenizer = transformers.AutoTokenizer.from_pretrained(
            self.model_revision,
            revision=self.model_revision,
        )
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            self.model_revision,
            revision=self.model_revision,
        )
        model.eval()
        label_map = _resolve_label_map(
            {int(index): str(label) for index, label in model.config.id2label.items()}
        )
        object.__setattr__(self, "_tokenizer", tokenizer)
        object.__setattr__(self, "_model", model)
        object.__setattr__(self, "_torch", torch)
        object.__setattr__(self, "_label_map", label_map)
        return self, label_map

    def classify(self, claim_text: str, evidence_text: str) -> dict[str, float | str]:
        backend, label_map = self._load()
        torch = backend._torch
        tokenizer = backend._tokenizer
        model = backend._model
        encoded = tokenizer(
            claim_text,
            evidence_text,
            return_tensors="pt",
            truncation=True,
        )
        with torch.inference_mode():
            logits = model(**encoded).logits[0]
            probabilities = torch.softmax(logits, dim=-1)
        index = int(torch.argmax(probabilities).item())
        return {
            "stance": label_map[index].value,
            "confidence": float(probabilities[index].item()),
        }
