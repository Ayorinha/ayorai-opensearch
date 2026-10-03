"""Stance detection contracts and deterministic/local/provider adapters."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from .extraction import ComponentProvenance, ExtractedClaim
from .models import Evidence, Stance, StanceEdge
from .numeric import DEFAULT_RELATIVE_TOLERANCE, NumericLocale, numeric_conflicts, parse_number

_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+|[.,]\d{3})*(?:\s*%)?")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NEGATIONS = frozenset({"not", "no", "didn't", "doesn't", "never", "não", "nao", "nunca", "sem", "não foi", "nao foi"})


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)


def _has_negation(text: str) -> bool:
    lowered = text.casefold()
    return any(token in lowered for token in _NEGATIONS)


@dataclass(frozen=True)
class DetectedStance:
    edge: StanceEdge
    confidence: float
    provenance: ComponentProvenance


@dataclass(frozen=True)
class StanceDetectionResult:
    edges: tuple[DetectedStance, ...]


class StanceDetector(Protocol):
    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        ...


class RuleStanceDetector:
    """Deterministic fixture detector.

    It recognizes direct lexical support, negation, and numeric/date conflicts.
    The output is still only a StanceEdge; the Judge decides the verdict.
    """

    component = "stance_detector.rule"
    model = "rule-fixture"
    version = "1"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        claim_numbers = _numbers(claim_text)
        evidence_numbers = _numbers(evidence_text)
        if not claim_numbers or not evidence_numbers:
            return False
        for left in claim_numbers:
            for right in evidence_numbers:
                try:
                    if numeric_conflicts(
                        left,
                        right,
                        locale=NumericLocale.EN_US,
                        tolerance=DEFAULT_RELATIVE_TOLERANCE,
                    ):
                        return True
                except ValueError:
                    continue
        return False

    @staticmethod
    def _date_conflict(claim_text: str, evidence_text: str) -> bool:
        claim_dates = set(_DATE_RE.findall(claim_text))
        evidence_dates = set(_DATE_RE.findall(evidence_text))
        return bool(claim_dates and evidence_dates and claim_dates.isdisjoint(evidence_dates))

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        by_id = {item.id: item for item in evidence}
        output: list[DetectedStance] = []
        for claim_item in claims:
            claim = claim_item.claim
            for evidence_id in claim_item.evidence_ids:
                item = by_id[evidence_id]
                claim_tokens = {
                    token.casefold()
                    for token in re.findall(r"[\wÀ-ÿ]+", claim.text)
                    if len(token) > 2
                }
                evidence_tokens = {
                    token.casefold()
                    for token in re.findall(r"[\wÀ-ÿ]+", item.excerpt)
                    if len(token) > 2
                }
                overlap = len(claim_tokens & evidence_tokens)
                lexical = overlap / max(len(claim_tokens), 1)
                baseline = by_id[claim_item.evidence_ids[0]]
                contradiction = (
                    self._numeric_conflict(claim.text, item.excerpt)
                    or self._date_conflict(claim.text, item.excerpt)
                    or self._numeric_conflict(baseline.excerpt, item.excerpt)
                    or self._date_conflict(baseline.excerpt, item.excerpt)
                )
                if _has_negation(claim.text) != _has_negation(item.excerpt):
                    if lexical >= 0.25:
                        contradiction = True
                if item.id != baseline.id and _has_negation(baseline.excerpt) != _has_negation(item.excerpt):
                    contradiction = True
                stance = Stance.CONTRADICTS if contradiction else Stance.SUPPORTS
                confidence = min(1.0, max(0.5, 0.5 + lexical / 2))
                payload = f"{claim.id}|{item.id}|{stance.value}"
                output.append(
                    DetectedStance(
                        edge=StanceEdge(
                            id=f"ste_{claim.id}_{item.id}",
                            claim_id=claim.id,
                            evidence_id=item.id,
                            stance=stance,
                        ),
                        confidence=confidence,
                        provenance=ComponentProvenance(
                            component=self.component,
                            model=self.model,
                            version=self.version,
                            input_sha256=_sha256(claim.text + "\n" + item.excerpt),
                            output_sha256=_sha256(payload),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class NLIStanceDetector:
    """Injected local NLI adapter; compatible with MiniCheck/DeBERTa-style backends."""

    component = "stance_detector.nli"

    def __init__(self, backend: Any, *, model: str, version: str) -> None:
        self.backend = backend
        self.model = model
        self.version = version

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        by_id = {item.id: item for item in evidence}
        output: list[DetectedStance] = []
        for claim_item in claims:
            for evidence_id in claim_item.evidence_ids:
                item = by_id[evidence_id]
                result = self.backend.classify(claim_item.claim.text, item.excerpt)
                stance = Stance(str(result["stance"]))
                confidence = float(result["confidence"])
                payload = json.dumps(result, ensure_ascii=False, sort_keys=True)
                output.append(
                    DetectedStance(
                        edge=StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=stance,
                        ),
                        confidence=confidence,
                        provenance=ComponentProvenance(
                            component=self.component,
                            model=self.model,
                            version=self.version,
                            input_sha256=_sha256(claim_item.claim.text + "\n" + item.excerpt),
                            output_sha256=_sha256(payload),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class LLMStanceDetector:
    """Provider-backed stance adapter expecting strict JSON and never a verdict."""

    component = "stance_detector.llm"

    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider = provider
        self.model = model
        self.version = version

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        by_id = {item.id: item for item in evidence}
        output: list[DetectedStance] = []
        for claim_item in claims:
            for evidence_id in claim_item.evidence_ids:
                item = by_id[evidence_id]
                prompt = json.dumps(
                    {
                        "task": "classify stance only",
                        "claim": claim_item.claim.text,
                        "evidence": item.excerpt,
                        "allowed_stance": ["supports", "contradicts"],
                        "output_schema": {"stance": "supports|contradicts", "confidence": "number"},
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                response = self.provider.execute(prompt)
                result = json.loads(response.text)
                stance = Stance(str(result["stance"]))
                confidence = float(result["confidence"])
                output.append(
                    DetectedStance(
                        edge=StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=stance,
                        ),
                        confidence=confidence,
                        provenance=ComponentProvenance(
                            component=self.component,
                            model=self.model,
                            version=self.version,
                            input_sha256=_sha256(prompt),
                            output_sha256=_sha256(response.text),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))
