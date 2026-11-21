"""AYORAI-PT-NLI inference integration (ADR-008): EuroBERT sequence-pair stance.

This module loads a *fine-tuned* EuroBERT checkpoint that classifies a claim
against an evidence passage into SUPPORTS, CONTRADICTS or NEUTRAL. It performs no
training, downloads nothing at import time and is never used by default: a caller
builds the detector explicitly and passes it to ``check_documents``.

Fail-closed rules:

* the model is loaded with ``trust_remote_code=False``; EuroBERT must be supported
  natively by the installed ``transformers`` (5.3.0 or later), so no Python code
  from a model repository is ever executed;
* the checkpoint revision is a full 40-character commit SHA, never a branch name;
* the checkpoint's ``model_type`` must be ``eurobert``;
* the checkpoint must expose exactly the labels entailment, contradiction and
  neutral. The public base model ``EuroBERT/EuroBERT-210m`` has no trained NLI head
  and is therefore rejected before any weight is loaded;
* weights without a recorded commercial-license audit (ADR-008 §§1 and 10) are
  ``UNAUDITED`` and load only in evaluation mode or with an explicit opt-in.

The detector only produces stance edges. The verdict stays with the deterministic
Judge (ADR-002/ADR-011), and the conservative wrapper still demands near-complete
lexical support before a SUPPORTS edge counts.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Any, Final

from .nli import TransformersNLIBackend, _resolve_label_map

BASE_MODEL_ID: Final = "EuroBERT/EuroBERT-210m"
# Revision checked on 2026-11-21 (model card licence: apache-2.0).
BASE_MODEL_REVISION: Final = "39b51e15dd1f1a06f58b5cbf6a8a188cec60bd0e"
BASE_MODEL_LICENSE: Final = "apache-2.0"
MIN_TRANSFORMERS_VERSION: Final = (5, 3, 0)
MAX_SEQUENCE_TOKENS: Final = 8192

UNAUDITED_LEVEL: Final = "UNAUDITED"
COMMERCIAL_AUDITED_LEVEL: Final = "COMMERCIAL_AUDITED"
LICENSE_LEVELS: Final = frozenset({UNAUDITED_LEVEL, COMMERCIAL_AUDITED_LEVEL})

_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


def _version_tuple(version: str) -> tuple[int, int, int]:
    numbers = [int(part) for part in re.findall(r"\d+", version)[:3]]
    while len(numbers) < 3:
        numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


@dataclass(frozen=True)
class PtNliCheckpoint:
    """An immutable reference to a fine-tuned AYORAI-PT-NLI checkpoint."""

    model_id: str
    revision: str
    license_level: str
    base_model_revision: str = BASE_MODEL_REVISION

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id is required")
        for name in ("revision", "base_model_revision"):
            value = getattr(self, name)
            if _COMMIT_SHA.fullmatch(value) is None:
                raise ValueError(f"{name} must be a full 40-character commit SHA")
        if self.license_level not in LICENSE_LEVELS:
            raise ValueError(f"license_level must be one of {sorted(LICENSE_LEVELS)}")


class EuroBertNLIBackend(TransformersNLIBackend):
    """Three-class NLI over a fine-tuned EuroBERT checkpoint, CPU, no remote code."""

    def __init__(
        self,
        checkpoint: PtNliCheckpoint,
        *,
        evaluation_mode: bool = False,
        license_opt_in: bool = False,
    ) -> None:
        # UNAUDITED weights follow the same gate as EVAL_ONLY models.
        level = "EVAL_ONLY" if checkpoint.license_level == UNAUDITED_LEVEL else "COMMERCIAL"
        super().__init__(
            checkpoint.model_id,
            checkpoint.revision,
            license_level=level,
            evaluation_mode=evaluation_mode,
            license_opt_in=license_opt_in,
        )
        self.checkpoint = checkpoint

    @property
    def provenance_version(self) -> str:
        return (
            f"{super().provenance_version}|ckpt_license={self.checkpoint.license_level}"
            f"|base={self.checkpoint.base_model_revision}|remote_code=false"
        )

    def _load(self) -> dict[int, str]:
        _ = self.provenance_version  # licence gate before any import or download
        label_map = self.__dict__["_label_map"]
        if label_map is not None:
            return {int(index): str(label) for index, label in label_map.items()}
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            raise RuntimeError("install the optional 'nli' extra to use AYORAI-PT-NLI") from exc
        if _version_tuple(str(transformers.__version__)) < MIN_TRANSFORMERS_VERSION:
            raise RuntimeError(
                "AYORAI-PT-NLI needs transformers>=5.3.0, which supports EuroBERT natively; "
                "remote model code is never enabled"
            )
        config = transformers.AutoConfig.from_pretrained(
            self.model_id, revision=self.model_revision, trust_remote_code=False
        )
        if getattr(config, "model_type", None) != "eurobert":
            raise ValueError("AYORAI-PT-NLI checkpoint must have model_type 'eurobert'")
        try:
            label_map = _resolve_label_map(
                {int(index): str(label) for index, label in config.id2label.items()}
            )
        except ValueError as exc:
            raise ValueError(
                "checkpoint has no trained NLI head (labels must be entailment, contradiction "
                "and neutral); the public EuroBERT base model cannot classify stance"
            ) from exc
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            self.model_id, revision=self.model_revision, trust_remote_code=False
        )
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            self.model_id, revision=self.model_revision, trust_remote_code=False
        )
        model.eval()
        self.__dict__["_tokenizer"] = tokenizer
        self.__dict__["_model"] = model
        self.__dict__["_torch"] = torch
        self.__dict__["_label_map"] = label_map
        return label_map

    def classify(self, claim_text: str, evidence_text: str) -> dict[str, float | str]:
        label_map = self._load()
        # Evidence first, claim second (the order used to train the head); only the
        # evidence is ever truncated, so the claim is always read in full.
        encoded = self.__dict__["_tokenizer"](
            evidence_text,
            claim_text,
            return_tensors="pt",
            truncation="only_first",
            max_length=MAX_SEQUENCE_TOKENS,
        )
        torch = self.__dict__["_torch"]
        with torch.inference_mode():
            logits = self.__dict__["_model"](**encoded).logits[0]
            probabilities = torch.softmax(logits, dim=-1)
        index = int(torch.argmax(probabilities).item())
        return {"stance": label_map[index], "confidence": float(probabilities[index].item())}


def build_pt_nli_detector(
    checkpoint: PtNliCheckpoint,
    *,
    evaluation_mode: bool = False,
    license_opt_in: bool = False,
    backend: Any | None = None,
) -> Any:
    """Return the conservative AYORAI-PT-NLI stance detector for ``check_documents``.

    ``backend`` exists for tests and offline evaluation; by default the EuroBERT
    backend above is used. Nothing is loaded until the first classification.
    """
    from .document_check import ConservativeStanceDetector
    from .stance import NLIStanceDetector

    nli_backend = backend or EuroBertNLIBackend(
        checkpoint, evaluation_mode=evaluation_mode, license_opt_in=license_opt_in
    )
    inner = NLIStanceDetector(
        nli_backend,
        model=f"ayorai-pt-nli:{checkpoint.model_id}",
        version=f"{checkpoint.revision}|license={checkpoint.license_level}",
        tie_precedence="contradicts",
    )
    return ConservativeStanceDetector(inner)
