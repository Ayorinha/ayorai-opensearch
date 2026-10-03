from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence
from .extraction import ComponentProvenance, ExtractedClaim
from .models import Evidence, Stance, StanceEdge
from .numeric import DEFAULT_RELATIVE_TOLERANCE, NumericLocale, numeric_conflicts

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
    def detect(self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]) -> StanceDetectionResult: ...

class RuleStanceDetector:
    component = "stance_detector.rule"
    model = "rule-fixture"
    version = "2"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        claim_numbers = _numbers(claim_text)
        evidence_numbers = _numbers(evidence_text)
        if not claim_numbers or not evidence_numbers:
            return False
        return any(
            numeric_conflicts(left, right, locale=NumericLocale.EN_US, tolerance=DEFAULT_RELATIVE_TOLERANCE)
            for left in claim_numbers for right in evidence_numbers
        )

    @staticmethod
    def _date_conflict(claim_text: str, evidence_text: str) -> bool:
        claim_dates = set(_DATE_RE.findall(claim_text))
        evidence_dates = set(_DATE_RE.findall(evidence_text))
        return bool(claim_dates and evidence_dates and claim_dates.isdisjoint(evidence_dates))

    def detect(self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]) -> StanceDetectionResult:
        output: list[DetectedStance] = []
        for claim_item in claims:
            claim_tokens = {t.casefold() for t in re.findall(r"[\wÀ-ÿ]+", claim_item.claim.text) if len(t) > 2}
            for item in (item for item in evidence if item.claim_id == claim_item.claim.id):
                evidence_tokens = {t.casefold() for t in re.findall(r"[\wÀ-ÿ]+", item.excerpt) if len(t) > 2}
                lexical = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
                if lexical < 0.25:
                    stance = Stance.NEUTRAL
                else:
                    contradiction = (
                        self._numeric_conflict(claim_item.claim.text, item.excerpt)
                        or self._date_conflict(claim_item.claim.text, item.excerpt)
                        or _has_negation(claim_item.claim.text) != _has_negation(item.excerpt)
                    )
                    stance = Stance.CONTRADICTS if contradiction else Stance.SUPPORTS
                payload = f"{claim_item.claim.id}|{item.id}|{stance.value}"
                output.append(DetectedStance(
                    edge=StanceEdge(id=f"ste_{claim_item.claim.id}_{item.id}", claim_id=claim_item.claim.id, evidence_id=item.id, stance=stance),
                    confidence=min(1.0, max(0.5, 0.5 + lexical / 2)),
                    provenance=ComponentProvenance(
                        component=self.component, model=self.model, version=self.version,
                        input_sha256=_sha256(claim_item.claim.text + "\n" + item.excerpt),
                        output_sha256=_sha256(payload),
                    ),
                ))
        return StanceDetectionResult(tuple(output))

class NLIStanceDetector:
    component = "stance_detector.nli"
    def __init__(self, backend: Any, *, model: str, version: str) -> None:
        self.backend, self.model, self.version = backend, model, version
    def detect(self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            for item in (item for item in evidence if item.claim_id == claim_item.claim.id):
                result = self.backend.classify(claim_item.claim.text, item.excerpt)
                stance = Stance(str(result["stance"]))
                output.append(DetectedStance(
                    edge=StanceEdge(id=f"ste_{claim_item.claim.id}_{item.id}", claim_id=claim_item.claim.id, evidence_id=item.id, stance=stance),
                    confidence=float(result["confidence"]),
                    provenance=ComponentProvenance(component=self.component, model=self.model, version=self.version, input_sha256=_sha256(claim_item.claim.text + "\n" + item.excerpt), output_sha256=_sha256(str(result))),
                ))
        return StanceDetectionResult(tuple(output))

class LLMStanceDetector:
    component = "stance_detector.llm"
    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider, self.model, self.version = provider, model, version
    def detect(self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]) -> StanceDetectionResult:
        import json
        output = []
        for claim_item in claims:
            for item in (item for item in evidence if item.claim_id == claim_item.claim.id):
                prompt = json.dumps({"task":"classify stance only","claim":claim_item.claim.text,"evidence":item.excerpt,"allowed_stance":["supports","contradicts","neutral"]}, ensure_ascii=False, sort_keys=True)
                response = self.provider.execute(prompt)
                result = json.loads(response.text)
                stance = Stance(str(result["stance"]))
                output.append(DetectedStance(
                    edge=StanceEdge(id=f"ste_{claim_item.claim.id}_{item.id}", claim_id=claim_item.claim.id, evidence_id=item.id, stance=stance),
                    confidence=float(result["confidence"]),
                    provenance=ComponentProvenance(component=self.component, model=self.model, version=self.version, input_sha256=_sha256(prompt), output_sha256=_sha256(response.text)),
                ))
        return StanceDetectionResult(tuple(output))
