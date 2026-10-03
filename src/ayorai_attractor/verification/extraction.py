"""Claim extraction contracts and deterministic/local/provider adapters.

Extraction is advisory: outputs become structured inputs to the deterministic
ADR-002 Judge and can never directly select a final verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, Sequence

from .models import Claim, Evidence

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_STOPWORDS = frozenset(
    {
        "a","o","as","os","um","uma","de","da","do","das","dos","em","no","na",
        "nos","nas","e","ou","que","qual","quais","quando","onde","como","foi",
        "foram","era","é","são","tem","tinha","para","por","segundo","the","a",
        "an","and","or","of","in","on","at","was","were","is","are","what","when",
        "where","how","did","does","do","the","to","for","according",
    }
)


def _tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(text)
        if token.casefold() not in _STOPWORDS and len(token) > 2
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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

    def to_evidence(self, claim_id: str) -> Evidence:
        end = self.end_offset if self.end_offset is not None else len(self.content)
        return Evidence(
            id=self.id,
            claim_id=claim_id,
            source_id=self.source_id,
            source_location=self.source_location,
            retrieved_at=self.retrieved_at,
            start_offset=self.start_offset,
            end_offset=end,
            excerpt=self.content,
            origin_id=self.origin_id,
            canonical_url=self.canonical_url,
            normalized_content_hash=self.normalized_content_hash or _sha256(self.content),
            cited_origin_id=self.cited_origin_id,
            provenance_complete=True,
        )


@dataclass(frozen=True)
class ExtractedClaim:
    claim: Claim
    evidence_ids: tuple[str, ...]
    confidence: float
    provenance: ComponentProvenance


@dataclass(frozen=True)
class ClaimExtractionResult:
    claims: tuple[ExtractedClaim, ...]


class ClaimExtractor(Protocol):
    def extract(
        self,
        query: str,
        documents: Sequence[RetrievedDocument],
    ) -> ClaimExtractionResult:
        ...


def _representative_sentence(text: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return sentences[0] if sentences else text.strip()


class RuleClaimExtractor:
    """Deterministic fixture/CI extractor based on lexical evidence grouping."""

    component = "claim_extractor.rule"
    model = "rule-fixture"
    version = "1"

    def extract(
        self,
        query: str,
        documents: Sequence[RetrievedDocument],
    ) -> ClaimExtractionResult:
        if not documents:
            return ClaimExtractionResult(())
        query_tokens = _tokens(query)
        interrogative = query.casefold().lstrip().startswith(
            ("qual ", "quais ", "quant", "quando ", "onde ", "how ", "what ", "when ", "where ")
        )
        groups: list[list[RetrievedDocument]] = []
        group_keys: list[set[str]] = []
        for document in documents:
            sentence = _representative_sentence(document.content)
            tokens = _tokens(sentence)
            overlap = tokens & query_tokens
            placed = False
            for index, key in enumerate(group_keys):
                if overlap & key or (not query_tokens and tokens & key):
                    groups[index].append(document)
                    group_keys[index].update(tokens)
                    placed = True
                    break
            if not placed:
                groups.append([document])
                group_keys.append(set(tokens))
        extracted: list[ExtractedClaim] = []
        for index, group in enumerate(groups, start=1):
            representative = _representative_sentence(group[0].content)
            text = representative if interrogative else query.rstrip(" ?.")
            if not text:
                continue
            evidence_ids = tuple(document.id for document in group)
            payload = json.dumps(
                {
                    "query": query,
                    "evidence_ids": evidence_ids,
                    "text": text,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            provenance = ComponentProvenance(
                component=self.component,
                model=self.model,
                version=self.version,
                input_sha256=_sha256(query + "\n" + "\n".join(evidence_ids)),
                output_sha256=_sha256(payload),
            )
            confidence = min(
                1.0,
                max(
                    0.5,
                    sum(
                        bool(_tokens(document.content) & query_tokens)
                        for document in group
                    )
                    / max(len(group), 1),
                ),
            )
            extracted.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=text),
                    evidence_ids=evidence_ids,
                    confidence=confidence,
                    provenance=provenance,
                )
            )
        return ClaimExtractionResult(tuple(extracted))


class NLIClaimExtractor:
    """Local NLI-backed extractor adapter.

    The backend is deliberately injected so MiniCheck, DeBERTa-NLI or another
    local model can be selected without coupling the verification core to a
    model package.
    """

    component = "claim_extractor.nli"

    def __init__(self, backend: Any, *, model: str, version: str) -> None:
        self.backend = backend
        self.model = model
        self.version = version

    def extract(
        self,
        query: str,
        documents: Sequence[RetrievedDocument],
    ) -> ClaimExtractionResult:
        raw = self.backend.extract_claims(query, [document.content for document in documents])
        claims: list[ExtractedClaim] = []
        for index, item in enumerate(raw, start=1):
            text = str(item["text"])
            evidence_ids = tuple(str(value) for value in item.get("evidence_ids", ()))
            confidence = float(item.get("confidence", 0.0))
            payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
            claims.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=text),
                    evidence_ids=evidence_ids,
                    confidence=confidence,
                    provenance=ComponentProvenance(
                        component=self.component,
                        model=self.model,
                        version=self.version,
                        input_sha256=_sha256(query),
                        output_sha256=_sha256(payload),
                    ),
                )
            )
        return ClaimExtractionResult(tuple(claims))


class LLMClaimExtractor:
    """Provider-backed claim extractor expecting strict JSON from the provider."""

    component = "claim_extractor.llm"

    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider = provider
        self.model = model
        self.version = version

    def extract(
        self,
        query: str,
        documents: Sequence[RetrievedDocument],
    ) -> ClaimExtractionResult:
        prompt = json.dumps(
            {
                "task": "extract factual claims and map each claim to evidence ids",
                "query": query,
                "documents": [
                    {"id": document.id, "content": document.content}
                    for document in documents
                ],
                "output_schema": {
                    "claims": [
                        {
                            "text": "string",
                            "evidence_ids": ["string"],
                            "confidence": "number",
                        }
                    ]
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        response = self.provider.execute(prompt)
        payload = json.loads(response.text)
        result = payload["claims"]
        claims: list[ExtractedClaim] = []
        for index, item in enumerate(result, start=1):
            claims.append(
                ExtractedClaim(
                    claim=Claim(id=f"clm_{index:03d}", text=str(item["text"])),
                    evidence_ids=tuple(str(value) for value in item["evidence_ids"]),
                    confidence=float(item["confidence"]),
                    provenance=ComponentProvenance(
                        component=self.component,
                        model=self.model,
                        version=self.version,
                        input_sha256=_sha256(prompt),
                        output_sha256=_sha256(response.text),
                    ),
                )
            )
        return ClaimExtractionResult(tuple(claims))
