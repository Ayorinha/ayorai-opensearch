from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ComponentProvenance, ExtractedClaim
from .models import Evidence, Stance, StanceEdge
from .numeric import DEFAULT_RELATIVE_TOLERANCE, NumericLocale, numeric_conflicts


class LLMStancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_id: str = Field(min_length=1)
    stance: Literal["supports", "contradicts", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)


_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+|[.,]\d{3})*(?:\s*%)?")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_NEGATION_TOKENS = frozenset(
    {"not", "no", "didn't", "doesn't", "never", "não", "nao", "nunca", "sem"}
)
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "for",
        "in",
        "on",
        "at",
        "to",
        "was",
        "were",
        "is",
        "are",
        "reported",
        "reports",
        "year",
        "fiscal",
        "de",
        "da",
        "do",
        "e",
        "em",
        "no",
        "na",
        "foi",
        "era",
        "é",
    }
)
_UNIT_WORDS = frozenset(
    {
        "usd", "eur", "brl", "ms", "million", "millions", "billion", "billions",
        "employees",
        "people",
        "customers",
        "offices",
        "percent",
        "rate",
        "year",
        "mil",
        "milhão",
        "milhões",
        "bilhão",
        "bilhões",
    }
)
_PT_MARKERS = frozenset(
    {"não", "nao", "uma", "para", "com", "que", "foi", "são", "sao",
     "empresa", "receita", "ano", "dos", "das", "em", "por"}
)
_ENTITY_RE = re.compile(r"\b(?:company|empresa)\s+[A-Z][\w-]*\b", re.UNICODE)
_EN_MARKERS = frozenset(
    {"the", "was", "were", "with", "that", "company", "revenue", "year",
     "from", "for", "and", "not", "this", "reported"}
)


def detect_language(text: str) -> str:
    tokens = {token.casefold() for token in _TOKEN_RE.findall(text)}
    pt = len(tokens & _PT_MARKERS) + sum(char in text for char in "ãõáéíóúç")
    en = len(tokens & _EN_MARKERS)
    return "pt" if pt > en else "en"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _has_negation(text: str) -> bool:
    return bool({token.casefold() for token in _TOKEN_RE.findall(text)} & _NEGATION_TOKENS)


def _numeric_facts(text: str) -> list[tuple[str, str, str]]:
    tokens = _TOKEN_RE.findall(text.casefold())
    facts = []
    for index, token in enumerate(tokens):
        if not _NUMBER_RE.fullmatch(token):
            continue
        before = tokens[max(0, index - 6) : index]
        after = tokens[index + 1 : index + 4]
        context = before + after
        if "%" in token or "percent" in context or "porcento" in context:
            unit = "percent"
        elif any(value in context for value in ("usd", "eur", "brl")):
            currency = next(
                value for value in ("usd", "eur", "brl") if value in context
            )
            scale = next(
                (
                    value
                    for value in (
                        "million",
                        "millions",
                        "milhão",
                        "milhões",
                        "billion",
                        "billions",
                        "bilhão",
                        "bilhões",
                    )
                    if value in context
                ),
                "",
            )
            scale_alias = {
                "million": "million", "millions": "million",
                "milhão": "million", "milhões": "million",
                "billion": "billion", "billions": "billion",
                "bilhão": "billion", "bilhões": "billion",
            }
            unit = f"{currency}:{scale_alias.get(scale, scale or 'base')}"
        elif "ms" in context:
            unit = "ms"
        elif "year" in context:
            unit = "year"
        elif any(value in context for value in ("employees", "people", "customers", "offices")):
            word = next(
                value
                for value in ("employees", "people", "customers", "offices")
                if value in context
            )
            unit = f"count:{word}"
        else:
            unit = "scalar"
        aliases = {
            "receita": "revenue",
            "faturamento": "revenue",
            "revenue": "revenue",
            "lucro": "profit",
            "profit": "profit",
            "custo": "cost",
            "cost": "cost",
        }
        context_candidates = before + after
        matched_attribute = next(
            (aliases[value] for value in context_candidates if value in aliases),
            None,
        )
        attribute = (
            "year"
            if unit == "year"
            else matched_attribute
            or next(
                (
                    value
                    for value in reversed(context_candidates)
                    if (
                        value not in _STOPWORDS
                        and value not in _UNIT_WORDS
                        and value not in _entities(text)
                    )
                ),
                "unknown",
            )
        )
        facts.append((token, unit, attribute))
    return facts


def _numeric_relation(claim_text: str, evidence_text: str) -> tuple[bool, bool]:
    conflict = False
    agreement = False
    for left, left_unit, left_attribute in _numeric_facts(claim_text):
        for right, right_unit, right_attribute in _numeric_facts(evidence_text):
            if left_unit != right_unit or left_attribute != right_attribute:
                continue
            if numeric_conflicts(
                left,
                right,
                locale=NumericLocale.EN_US,
                tolerance=DEFAULT_RELATIVE_TOLERANCE,
            ):
                conflict = True
            else:
                agreement = True
    return conflict, agreement


def _entities(text: str) -> set[str]:
    return {match.group(0).casefold() for match in _ENTITY_RE.finditer(text)}


def _numeric_facts_align(
    claim_text: str, evidence_text: str
) -> tuple[bool, bool, bool]:
    claim_entities = _entities(claim_text)
    evidence_entities = _entities(evidence_text)
    if claim_entities and not claim_entities.intersection(evidence_entities):
        return False, False, False
    claim_facts = _numeric_facts(claim_text)
    evidence_facts = _numeric_facts(evidence_text)
    if not claim_facts:
        return False, False, True
    conflict = False
    agreement = False
    matched = False
    for left, left_unit, left_attribute in claim_facts:
        for right, right_unit, right_attribute in evidence_facts:
            if left_unit != right_unit or left_attribute != right_attribute:
                continue
            matched = True
            if numeric_conflicts(
                left, right,
                locale=NumericLocale.EN_US,
                tolerance=DEFAULT_RELATIVE_TOLERANCE,
            ):
                conflict = True
            else:
                agreement = True
    return conflict, agreement, matched


def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
    return _numeric_relation(claim_text, evidence_text)[0]


def _numeric_agreement(claim_text: str, evidence_text: str) -> bool:
    return _numeric_relation(claim_text, evidence_text)[1]


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
    component = "stance_detector.rule"
    model = "rule-fixture"
    version = "4"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        return _numeric_conflict(claim_text, evidence_text)

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
        output = []
        for claim_item in claims:
            claim_tokens = {
                token.casefold()
                for token in _TOKEN_RE.findall(claim_item.claim.text)
                if len(token) > 2
            }
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                evidence_tokens = {
                    token.casefold()
                    for token in _TOKEN_RE.findall(item.excerpt)
                    if len(token) > 2
                }
                lexical = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
                numeric_conflict, numeric_agreement, numeric_matched = _numeric_facts_align(
                    claim_item.claim.text, item.excerpt
                )
                claim_has_numeric = bool(_numeric_facts(claim_item.claim.text))
                claim_has_date = bool(_DATE_RE.findall(claim_item.claim.text))
                claim_entities = _entities(claim_item.claim.text)
                evidence_entities = _entities(item.excerpt)
                entity_mismatch = bool(
                    claim_entities and not claim_entities.intersection(evidence_entities)
                )
                date_conflict = self._date_conflict(claim_item.claim.text, item.excerpt)
                evidence_has_date = bool(_DATE_RE.findall(item.excerpt))
                negation_conflict = _has_negation(claim_item.claim.text) != _has_negation(
                    item.excerpt
                )
                unverified_structured_fact = (
                    (claim_has_numeric and not numeric_matched)
                    or (claim_has_date and not evidence_has_date)
                    or entity_mismatch
                )
                if numeric_conflict or date_conflict or negation_conflict:
                    stance = Stance.CONTRADICTS
                elif unverified_structured_fact:
                    stance = Stance.NEUTRAL
                elif numeric_agreement:
                    stance = Stance.SUPPORTS
                elif lexical < 0.25:
                    stance = Stance.NEUTRAL
                else:
                    stance = Stance.SUPPORTS
                payload = f"{claim_item.claim.id}|{item.id}|{stance.value}"
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=stance,
                        ),
                        min(1.0, max(0.5, 0.5 + lexical / 2)),
                        ComponentProvenance(
                            self.component,
                            self.model,
                            self.version,
                            _sha256(claim_item.claim.text + "\
" + item.excerpt),
                            _sha256(payload),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class NLIStanceDetector:
    component = "stance_detector.nli"

    def __init__(
        self,
        backend: Any,
        *,
        model: str,
        version: str,
        window_size: int = 512,
        window_overlap: int = 64,
        tie_precedence: str = "contradicts",
    ) -> None:
        if window_size <= 0 or window_overlap < 0 or window_overlap >= window_size:
            raise ValueError("invalid evidence window configuration")
        if tie_precedence not in {"contradicts", "supports", "neutral"}:
            raise ValueError("invalid stance tie precedence")
        self.backend = backend
        self.model = model
        self.version = version
        self.window_size = window_size
        self.window_overlap = window_overlap
        self.tie_precedence = tie_precedence

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        text = evidence.excerpt
        if len(text) <= self.window_size:
            return [(evidence.start_offset, evidence.end_offset, text)]
        step = self.window_size - self.window_overlap
        windows = []
        for start in range(0, len(text), step):
            end = min(len(text), start + self.window_size)
            windows.append(
                (evidence.start_offset + start, evidence.start_offset + end, text[start:end])
            )
            if end == len(text):
                break
        return windows

    def _choose(
        self,
        candidates: list[tuple[str, float, int, int]],
    ) -> tuple[str, float, int, int]:
        priority = {"contradicts": 2, "supports": 1, "neutral": 0}
        if self.tie_precedence == "supports":
            priority["supports"] = 3
        elif self.tie_precedence == "neutral":
            priority["neutral"] = 3
        return max(candidates, key=lambda item: (item[1], priority[item[0]]))

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                candidates = []
                for start, end, window in self._windows(item):
                    result = self.backend.classify(claim_item.claim.text, window)
                    candidates.append(
                        (
                            str(result["stance"]),
                            float(result["confidence"]),
                            start,
                            end,
                        )
                    )
                stance, confidence, start, end = self._choose(candidates)
                local_start = start - item.start_offset
                local_end = end - item.start_offset
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(stance),
                        ),
                        confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            f"{self.version}|window={start}:{end}",
                            _sha256(
                                claim_item.claim.text + "\
"
                                + item.excerpt[local_start:local_end]
                            ),
                            _sha256(f"{stance}|{confidence:.12f}|{start}|{end}"),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class TranslatedNLIStanceDetector(NLIStanceDetector):
    component = "stance_detector.translate_nli"

    def __init__(
        self,
        backend: Any,
        translator: Any,
        *,
        model: str,
        version: str,
        window_size: int = 512,
        window_overlap: int = 64,
        tie_precedence: str = "contradicts",
    ) -> None:
        super().__init__(
            backend,
            model=model,
            version=version,
            window_size=window_size,
            window_overlap=window_overlap,
            tie_precedence=tie_precedence,
        )
        self.translator = translator

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                claim = claim_item.claim.text
                document = item.excerpt
                claim_lang = detect_language(claim)
                document_lang = detect_language(document)
                translated_claim = claim
                translated_document = document
                translation_hash = "none"
                if claim_lang != document_lang:
                    if claim_lang == "pt":
                        translated_claim = self.translator.translate(claim)
                        translation_hash = self.translator.provenance_hash(
                            claim, translated_claim
                        )
                    elif document_lang == "pt":
                        translated_document = self.translator.translate(document)
                        translation_hash = self.translator.provenance_hash(
                            document, translated_document
                        )
                temp_evidence = item.model_copy(update={"excerpt": translated_document})
                candidates = []
                for start, end, window in self._windows(temp_evidence):
                    result = self.backend.classify(translated_claim, window)
                    candidates.append(
                        (
                            str(result["stance"]),
                            float(result["confidence"]),
                            start,
                            end,
                        )
                    )
                stance, confidence, start, end = self._choose(candidates)
                local_start = start - temp_evidence.start_offset
                local_end = end - temp_evidence.start_offset
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(stance),
                        ),
                        confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            f"{self.version}|window={start}:{end}|translation={translation_hash}",
                            _sha256(
                                translated_claim + "\
"
                                + translated_document[local_start:local_end]
                            ),
                            _sha256(
                                f"{stance}|{confidence:.12f}|{start}|{end}|{translation_hash}"
                            ),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))



class LLMStanceDetector:
    component = "stance_detector.llm"

    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider, self.model, self.version = provider, model, version

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        import json

        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                prompt = json.dumps(
                    {
                        "task": "classify stance only",
                        "claim": claim_item.claim.text,
                        "evidence": item.excerpt,
                        "allowed_stance": ["supports", "contradicts", "neutral"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                response = self.provider.execute(prompt)
                try:
                    result = LLMStancePayload.model_validate(json.loads(response.text))
                except Exception as exc:
                    raise ValueError(f"invalid stance payload: {exc}") from exc
                if result.evidence_id != item.id:
                    raise ValueError(f"unknown evidence id: {result.evidence_id}")
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(result.stance),
                        ),
                        result.confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            self.version,
                            _sha256(prompt),
                            _sha256(response.text),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))
