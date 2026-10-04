from __future__ import annotations

import importlib

_LABEL_TO_STANCE = {
    "entailment": "supports",
    "contradiction": "contradicts",
    "neutral": "neutral",
}

EVAL_ONLY_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
EVAL_ONLY_REVISION = "b5113eb38ab63efdd7f280f8c144ea8b13f978ce"
EVAL_ONLY_LEVEL = "EVAL_ONLY"


def _resolve_label_map(id2label: dict[int, str]) -> dict[int, str]:
    normalized = {index: label.strip().casefold() for index, label in id2label.items()}
    if set(normalized.values()) != set(_LABEL_TO_STANCE):
        raise ValueError(
            "NLI model must expose exactly entailment, contradiction and neutral labels"
        )
    return {index: _LABEL_TO_STANCE[label] for index, label in normalized.items()}


def _license_guard(level: str, *, evaluation_mode: bool, license_opt_in: bool) -> str:
    if level == EVAL_ONLY_LEVEL and not evaluation_mode and not license_opt_in:
        raise PermissionError(
            "EVAL_ONLY model rejected outside evaluation mode; explicit license_opt_in is required"
        )
    if evaluation_mode:
        return "evaluation_mode=true"
    if license_opt_in:
        return "license_opt_in=true"
    return "license_opt_in=false"


class TransformersNLIBackend:
    """CPU-only three-class NLI backend with explicit license enforcement."""

    def __init__(
        self,
        model_id: str,
        model_revision: str,
        *,
        license_level: str = "COMMERCIAL_DEFAULT",
        evaluation_mode: bool = False,
        license_opt_in: bool = False,
    ) -> None:
        if not model_id.strip() or not model_revision.strip():
            raise ValueError("model_id and model_revision are required")
        self.model_id = model_id
        self.model_revision = model_revision
        self.license_level = license_level
        self.evaluation_mode = evaluation_mode
        self.license_opt_in = license_opt_in
        self.__dict__["_label_map"] = None
        self.__dict__["_tokenizer"] = None
        self.__dict__["_model"] = None
        self.__dict__["_torch"] = None

    @property
    def provenance_version(self) -> str:
        gate = _license_guard(
            self.license_level,
            evaluation_mode=self.evaluation_mode,
            license_opt_in=self.license_opt_in,
        )
        return f"{self.model_revision}|license={self.license_level}|{gate}"

    def _load(self) -> dict[int, str]:
        _ = self.provenance_version
        label_map = self.__dict__["_label_map"]
        if label_map is not None:
            return {int(index): str(label) for index, label in label_map.items()}

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
            use_fast=False,
        )
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            self.model_id,
            revision=self.model_revision,
        )
        model.eval()
        label_map = _resolve_label_map(
            {int(index): str(label) for index, label in model.config.id2label.items()}
        )
        self.__dict__["_tokenizer"] = tokenizer
        self.__dict__["_model"] = model
        self.__dict__["_torch"] = torch
        self.__dict__["_label_map"] = label_map
        return label_map

    def classify(self, claim_text: str, evidence_text: str) -> dict[str, float | str]:
        label_map = self._load()
        encoded = self.__dict__["_tokenizer"](
            evidence_text,
            claim_text,
            return_tensors="pt",
            truncation=True,
        )
        torch = self.__dict__["_torch"]
        with torch.inference_mode():
            logits = self.__dict__["_model"](**encoded).logits[0]
            probabilities = torch.softmax(logits, dim=-1)
        index = int(torch.argmax(probabilities).item())
        return {
            "stance": label_map[index],
            "confidence": float(probabilities[index].item()),
        }
