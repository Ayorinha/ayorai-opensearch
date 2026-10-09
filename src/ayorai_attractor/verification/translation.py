from __future__ import annotations

import hashlib
import importlib

from .nli import _license_guard

_ALLOWED_LICENSE_LEVELS = frozenset({"COMMERCIAL_DEFAULT", "EVAL_ONLY"})


class MarianTranslationBackend:
    """Lazy CPU MarianMT backend pinned to an immutable model revision.

    The license level must be supplied explicitly from
    docs/legal/MODEL-LICENSE-POLICY.md. Restricted models use the shared NLI
    license guard; provenance records the active guard state.
    """

    def __init__(
        self,
        model_id: str,
        model_revision: str,
        *,
        license_level: str,
        evaluation_mode: bool = False,
        license_opt_in: bool = False,
    ) -> None:
        if not model_id.strip() or not model_revision.strip():
            raise ValueError("model_id and model_revision are required")
        if license_level not in _ALLOWED_LICENSE_LEVELS:
            allowed = ", ".join(sorted(_ALLOWED_LICENSE_LEVELS))
            raise ValueError(f"license_level must be one of: {allowed}")
        self.model_id = model_id
        self.model_revision = model_revision
        self.license_level = license_level
        self.evaluation_mode = evaluation_mode
        self.license_opt_in = license_opt_in
        self.__dict__["_tokenizer"] = None
        self.__dict__["_model"] = None

    @property
    def provenance_version(self) -> str:
        gate = _license_guard(
            self.license_level,
            evaluation_mode=self.evaluation_mode,
            license_opt_in=self.license_opt_in,
        )
        return (
            f"{self.model_id}@{self.model_revision}"
            f"|license={self.license_level}|{gate}"
        )

    def _load(self) -> None:
        _ = self.provenance_version
        if self.__dict__["_model"] is not None:
            return
        try:
            transformers = importlib.import_module("transformers")
        except ImportError as exc:
            raise RuntimeError(
                "install the optional 'nli' extra to use MarianTranslationBackend"
            ) from exc
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            self.model_id,
            revision=self.model_revision,
            use_fast=False,
        )
        model = transformers.AutoModelForSeq2SeqLM.from_pretrained(
            self.model_id,
            revision=self.model_revision,
        )
        model.eval()
        self.__dict__["_tokenizer"] = tokenizer
        self.__dict__["_model"] = model

    def translate(self, text: str) -> str:
        self._load()
        tokenizer = self.__dict__["_tokenizer"]
        model = self.__dict__["_model"]
        encoded = tokenizer(text, return_tensors="pt", truncation=True)
        generated = model.generate(**encoded)
        return str(tokenizer.decode(generated[0], skip_special_tokens=True))

    def provenance_hash(self, original: str, translated: str) -> str:
        payload = (
            f"{self.provenance_version}\n"
            f"{hashlib.sha256(original.encode('utf-8')).hexdigest()}\n"
            f"{hashlib.sha256(translated.encode('utf-8')).hexdigest()}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
