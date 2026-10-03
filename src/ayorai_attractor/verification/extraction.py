"""Claim extraction contracts: decompose model responses, never evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .models import Claim, Evidence


class LLMClaimPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class LLMClaimResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    claims: list[LLMClaimPayload] = Field(min_length=1)


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _representative_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text.strip()) if part.strip()]


@dataclass(frozen=True)
class ComponentProvenance:
    component: str
    model: str
    version: str
    input_sha256: str
    output_sha256: str

    def as_dict(self) -> dict[str, str]:
        return {
            "component": self.component,
            "model": self.model,
            "version": self.version,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
        }


@dataclass(frozen=True)
class RetrievedDocument:
    id: str
    content: str
    source_id: str
    source_location: str
    retrieved_at: datetime
    start_offset: int = 0
    end_offset: int | None = None
    origin_id: str | None = None
    canonical_url: str | None = None
    normalized_content_hash: str | None = None
    cited_origin_id: str | None = None
    locale: str = "en-US"
    provenance_complete: bool = True

    def to_evidence(self, claim_id: str, *, evidence_id: str | None = None) -> Evidence:
        end = self.end_offset if self.end_offset is not None else len(self.content)
        return Evidence(
            id=evidence_id or self.id,
            claim_id=claim_id,
            source_id=self.source_id,
            source_location=self.source_location,
            retrieved_at=self.retrieved_at,
            start_offset=self.start_offset,
            end_offset=end,
            excerpt=self.content,
            origin_id=self.origin_id,
            canonical_url=HttpUrl(self.canonical_url) if self.canonical_url else None,
            normalized_content_hash=self.normalized_content_hash or _sha256(self.content),
            cited_origin_id=self.cited_origin_id,
            provenance_complete=self.provenance_complete,
        )


@dataclass(frozen=True)
class ExtractedClaim:
    claim: Claim
    confidence: float
    provenance: ComponentProvenance


@dataclass(frozen=True)
class ClaimExtractionResult:
    claims: tuple[ExtractedClaim, ...]


class ClaimExtractor(Protocol):
    """Decompose a model response into atomic claims.

    The extractor receives only the response. Evidence is deliberately absent
    from this contract to prevent circular verification.
    """

    def extract(self, response: str) -> ClaimExtractionResult:
        ...


class RuleClaimExtractor:
    """Deterministic sentence-based response decomposition for CI."""

    component = "claim_extractor.rule"
    model = "rule-fixture"
    version = "2"

    def extract(self, response: str) -> ClaimExtractionResult:
        sentences = _representative_sentences(response)
        claims: list[ExtractedClaim] = []
        for index, text in enumerate(sentences, start=1):
            payload = json.dumps({"text": text}, ensure_ascii=False, sort_keys=True)
            claims.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=text),
                    confidence=1.0,
                    provenance=ComponentProvenance(
                        component=self.component,
                        model=self.model,
                        version=self.version,
                        input_sha256=_sha256(response),
                        output_sha256=_sha256(payload),
                    ),
                )
            )
        return ClaimExtractionResult(tuple(claims))


class NLIClaimExtractor:
    """Injected local model adapter for atomic claim decomposition."""

    component = "claim_extractor.nli"

    def __init__(self, backend: Any, *, model: str, version: str) -> None:
        self.backend = backend
        self.model = model
        self.version = version

    def extract(self, response: str) -> ClaimExtractionResult:
        raw = self.backend.extract_claims(response)
        claims: list[ExtractedClaim] = []
        for index, item in enumerate(raw, start=1):
            text = str(item["text"])
            payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
            claims.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=text),
                    confidence=float(item.get("confidence", 0.0)),
                    provenance=ComponentProvenance(
                        component=self.component,
                        model=self.model,
                        version=self.version,
                        input_sha256=_sha256(response),
                        output_sha256=_sha256(payload),
                    ),
                )
            )
        return ClaimExtractionResult(tuple(claims))


class LLMClaimExtractor:
    """Provider-backed atomic claim extractor."""

    component = "claim_extractor.llm"

    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider = provider
        self.model = model
        self.version = version

    def extract(self, response: str) -> ClaimExtractionResult:
        prompt = json.dumps(
            {
                "task": "decompose the model response into atomic factual claims",
                "response": response,
                "output_schema": {
                    "claims": [{"text": "string", "confidence": "number"}]
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        provider_response = self.provider.execute(prompt)
        payload = LLMClaimResponse.model_validate(json.loads(provider_response.text))
        claims: list[ExtractedClaim] = []
        for index, item in enumerate(payload.claims, start=1):
            claims.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=item.text),
                    confidence=item.confidence,
                    provenance=ComponentProvenance(
                        component=self.component,
                        model=self.model,
                        version=self.version,
                        input_sha256=_sha256(response),
                        output_sha256=_sha256(provider_response.text),
                    ),
                )
            )
        return ClaimExtractionResult(tuple(claims))
