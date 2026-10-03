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
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_NEGATIONS = frozenset({"not", "no", "didn't", "doesn't", "never", "não", "nao", "nunca", "sem", "não foi", "nao foi"})
_STOPWORDS = frozenset({"the", "a", "an", "and", "or", "of", "for", "in", "on", "at", "to", "was", "were", "is", "are", "reported", "reports", "reported", "year", "fiscal", "de", "da", "do", "e", "em", "no", "na", "foi", "era", "é"})
_UNIT_WORDS = frozenset({"usd", "eur", "brl", "ms", "million", "millions", "billion", "billions", "employees", "people", "customers", "offices", "percent", "rate", "year"})

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)

def _has_negation(text: str) -> bool:
    lowered = text.casefold()
    return any(token in lowered for token in _NEGATIONS)

def _numeric_facts(text: str) -> list[tuple[str, str, str]]:
    tokens = _TOKEN_RE.findall(text.casefold())
    facts: list[tuple[str, str, str]] = []
    for index, token in enumerate(tokens):
        if not _NUMBER_RE.fullmatch(token):
            continue
        before = tokens[max(0, index - 6):index]
        after = tokens[index + 1:index + 4]
        context = before + after
        if "%" in token or "percent" in context:
            unit = "percent"
        elif any(value in context for value in ("usd", "eur", "brl")):
            currency = next(value for value in ("usd", "eur", "brl") if value in context)
            scale = next((value for value in ("million", "millions", "billion", "billions") if value in context), "")
            unit = f"{currency}:{scale or 'base'}"
        elif "ms" in context:
            unit = "ms"
        elif "year" in context:
            unit = "year"
        elif any(value in context for value in ("employees", "people", "customers", "offices")):
            count_word = next(value for value in ("employees", "people", "customers", "offices") if value in context)
            unit = f"count:{count_word}"
        else:
            unit = "scalar"
        attribute = next((value for value in reversed(before) if value not in _STOPWORDS and value not in _UNIT_WORDS), "unknown")
        if unit == "year":
            attribute = "year"
        facts.append((token, unit, attribute))
    return facts

def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
    claim_facts = _numeric_facts(claim_text)
    evidence_facts = _numeric_facts(evidence_text)
    for left, left_unit, left_attribute in claim_facts:
        for right, right_unit, right_attribute in evidence_facts:
            if left_unit != right_unit or left_attribute != right_attribute:
                continue
            if numeric_conflicts(left, right, locale=NumericLocale.EN_US, tolerance=DEFAULT_RELATIVE_TOLERANCE):
                return True
    return False

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
    version = "3"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        return _numeric_conflict(claim_text, evidence_text)

    @staticmethod
    def _date_conflict(claim_text: str, evidence_text: str) -> bool:
        claim_dates = set(_DATE_RE.findall(claim_text))
        evidence_dates = set(_DATE_RE.findall(evidence_text))
        return bool(claim_dates and evidence_dates and claim_dates.isdisjoint(evidence_dates))

    def detect(self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]) -> StanceDetectionResult:
        output: list[DetectedStance] = []
        for claim_item in claims:
            claim_tokens = {t.casefold() for t in _TOKEN_RE.findall(claim_item.claim.text) if len(t) > 2}
            for item in (item for item in evidence if item.claim_id == claim_item.claim.id):
                evidence_tokens = {t.casefold() for t in _TOKEN_RE.findall(item.excerpt) if len(t) > 2}
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
                    provenance=ComponentProvenance(self.component, self.model, self.version, _sha256(claim_item.claim.text + "\n" + item.excerpt), _sha256(payload)),
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
                output.append(DetectedStance(
                    edge=StanceEdge(id=f"ste_{claim_item.claim.id}_{item.id}", claim_id=claim_item.claim.id, evidence_id=item.id, stance=Stance(str(result["stance"]))),
                    confidence=float(result["confidence"]),
                    provenance=ComponentProvenance(self.component, self.model, self.version, _sha256(claim_item.claim.text + "\n" + item.excerpt), _sha256(str(result))),
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
                output.append(DetectedStance(
                    edge=StanceEdge(id=f"ste_{claim_item.claim.id}_{item.id}", claim_id=claim_item.claim.id, evidence_id=item.id, stance=Stance(str(result["stance"]))),
                    confidence=float(result["confidence"]),
                    provenance=ComponentProvenance(self.component, self.model, self.version, _sha256(prompt), _sha256(response.text)),
                ))
        return StanceDetectionResult(tuple(output))
