from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ComponentProvenance, ExtractedClaim
from .models import Evidence, Stance, StanceEdge
from .numeric import (
    DEFAULT_RELATIVE_TOLERANCE,
    NumericLocale,
    parse_number,
    relative_difference,
)


class LLMStancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_id: str = Field(min_length=1)
    stance: Literal["supports", "contradicts", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)


_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+|[.,]\d{3})*(?:\s*%)?")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
# Negation is language dependent. In Portuguese "no"/"na"/"nos"/"nas" are
# contractions of em + article ("no fim de 2025") and "sem" ("sem custo")
# does not negate the predicate, so neither counts as negation there.
_NEGATION_TOKENS_EN = frozenset({"not", "no", "didn't", "doesn't", "never"})
_NEGATION_TOKENS_PT = frozenset(
    {"não", "nao", "nunca", "jamais", "nem", "nenhum", "nenhuma", "ninguém", "ninguem"}
)
_NEGATION_TOKENS = _NEGATION_TOKENS_EN | _NEGATION_TOKENS_PT
# Portuguese-only function words used solely to decide whether "no" is English.
_PT_FUNCTION_WORDS = frozenset(
    {"de", "do", "da", "dos", "das", "um", "os", "as", "ao", "aos", "pelo", "pela", "também"}
)

_PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_PT_MONTH_PATTERN = "|".join(sorted(_PT_MONTHS, key=len, reverse=True))
_PT_DAY_DATE_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:º|°|o)?\s+de\s+(?P<month>{_PT_MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)
_PT_MONTH_DATE_RE = re.compile(
    rf"\b(?P<month>{_PT_MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)
_SLASH_DATE_RE = re.compile(r"\b(?P<a>\d{1,2})/(?P<b>\d{1,2})/(?P<year>\d{4})\b")

# Directional predicates: (axis, polarity). Opposite polarity on the same axis
# for the same proposition is a contradiction even when the numbers coincide.
_DIRECTION_TERMS: dict[str, tuple[str, int]] = {
    **dict.fromkeys(
        (
            "subiu", "subiram", "sobe", "sobem", "subir",
            "aumentou", "aumentaram", "aumenta", "aumentam", "aumentar", "aumento",
            "cresceu", "cresceram", "cresce", "crescem", "crescer", "crescimento",
            "increased", "increase", "increases", "rose", "rise", "rises",
            "grew", "grow", "grows",
        ),
        ("change", 1),
    ),
    **dict.fromkeys(
        (
            "caiu", "caíram", "cairam", "cai", "caem", "cair", "queda",
            "diminuiu", "diminuíram", "diminuiram", "diminui", "diminuem", "diminuir",
            "diminuição", "diminuicao",
            "reduziu", "reduziram", "reduz", "reduzem", "redução", "reducao",
            "encolheu", "encolheram", "encolhe", "encolhem",
            "decreased", "decrease", "decreases", "fell", "fall", "falls",
            "declined", "decline", "declines", "dropped", "drop", "drops",
        ),
        ("change", -1),
    ),
    **dict.fromkeys(
        (
            "aprovou", "aprovaram", "aprova", "aprovam", "aprovado", "aprovada",
            "aprovados", "aprovadas", "aprovação", "aprovacao",
            "approved", "approves", "approve",
        ),
        ("approval", 1),
    ),
    **dict.fromkeys(
        (
            "rejeitou", "rejeitaram", "rejeita", "rejeitam", "rejeitado", "rejeitada",
            "rejeitados", "rejeitadas", "rejeição", "rejeicao",
            "reprovou", "reprovaram", "reprovado", "reprovada",
            "vetou", "vetaram", "vetado", "vetada",
            "rejected", "rejects", "reject",
        ),
        ("approval", -1),
    ),
}
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
_ENTITY_PATTERN = r"\b(?:company|empresa)\s+(?P<name>[A-Za-zÀ-ÿ][\wÀ-ÿ-]*)\b"
_ENTITY_RE = re.compile(
    r"\b(?:company|empresa)\s+(?P<name>[A-Za-zÀ-ÿ][\wÀ-ÿ-]*)\b",
    re.IGNORECASE | re.UNICODE,
)
_EN_MARKERS = frozenset(
    {"the", "was", "were", "with", "that", "company", "revenue", "year",
     "from", "for", "and", "not", "this", "reported"}
)


def _language_scores(text: str) -> tuple[int, int]:
    tokens = {token.casefold() for token in _TOKEN_RE.findall(text)}
    pt = len(tokens & _PT_MARKERS) + sum(char in text for char in "ãõáéíóúç")
    en = len(tokens & _EN_MARKERS)
    return pt, en


def detect_language(text: str) -> str:
    pt, en = _language_scores(text)
    return "pt" if pt > en else "en"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _has_negation(text: str) -> bool:
    """Return True when the text negates its predicate.

    Portuguese negators always count. The English-only token "no" counts only
    when the text is more English than Portuguese, so Portuguese contractions
    ("no fim de 2025") and "sem" ("sem custo adicional") are not negation.
    """
    tokens = {token.casefold() for token in _TOKEN_RE.findall(text)}
    if tokens & _NEGATION_TOKENS_PT:
        return True
    pt, en = _language_scores(text)
    pt += len(tokens & _PT_FUNCTION_WORDS)
    if en >= pt:
        return bool(tokens & _NEGATION_TOKENS_EN)
    return bool(tokens & (_NEGATION_TOKENS_EN - {"no"}))


def _directions(text: str) -> dict[str, set[int]]:
    """Return the directional polarities asserted per axis."""
    found: dict[str, set[int]] = {}
    for token in _TOKEN_RE.findall(text):
        term = _DIRECTION_TERMS.get(token.casefold())
        if term is not None:
            found.setdefault(term[0], set()).add(term[1])
    return found


def _direction_conflict(claim_text: str, evidence_text: str) -> bool:
    """Opposite direction on a shared axis, with no same-direction support.

    Negated text is excluded: polarity reasoning under negation is left to the
    negation rule, so "não caiu" is never treated as "subiu".
    """
    if _has_negation(claim_text) or _has_negation(evidence_text):
        return False
    claim_directions = _directions(claim_text)
    evidence_directions = _directions(evidence_text)
    for axis, claim_polarities in claim_directions.items():
        evidence_polarities = evidence_directions.get(axis)
        if not evidence_polarities or len(claim_polarities) != 1:
            continue
        if not claim_polarities & evidence_polarities:
            return True
    return False


DateKey = tuple[str, int, int, int]


def _slash_date(first: int, second: int, year: int, language: str) -> DateKey | None:
    day, month = (first, second) if language == "pt" else (second, first)
    try:
        date(year, month, day)
    except ValueError:
        return None
    return ("day", year, month, day)


def _extract_dates(text: str) -> set[DateKey]:
    """Extract dates with the granularity the text asserts.

    Supports ISO `2026-03-10`, `10 de março de 2026`, `1º de abril de 2026`,
    `10/03/2026` (day/month in Portuguese, month/day in English) and
    `março de 2026` (month granularity). Invalid calendar dates are ignored.
    """
    found: set[DateKey] = set()
    for match in _DATE_RE.finditer(text):
        try:
            parsed = date.fromisoformat(match.group(0))
        except ValueError:
            continue
        found.add(("day", parsed.year, parsed.month, parsed.day))
    day_spans: list[tuple[int, int]] = []
    for match in _PT_DAY_DATE_RE.finditer(text):
        year = int(match.group("year"))
        month = _PT_MONTHS[match.group("month").casefold()]
        day = int(match.group("day"))
        day_spans.append(match.span())
        try:
            date(year, month, day)
        except ValueError:
            continue
        found.add(("day", year, month, day))
    for match in _PT_MONTH_DATE_RE.finditer(text):
        start = match.start()
        if any(left <= start < right for left, right in day_spans):
            continue
        month = _PT_MONTHS[match.group("month").casefold()]
        found.add(("month", int(match.group("year")), month, 0))
    language = detect_language(text)
    for match in _SLASH_DATE_RE.finditer(text):
        key = _slash_date(
            int(match.group("a")), int(match.group("b")), int(match.group("year")), language
        )
        if key is not None:
            found.add(key)
    return found


def _same_date(left: DateKey, right: DateKey) -> bool:
    """Compare at the coarser of the two asserted granularities."""
    if left[0] == "month" or right[0] == "month":
        return left[1:3] == right[1:3]
    return left == right


def _dates_conflict(claim_text: str, evidence_text: str) -> bool:
    claim_dates = _extract_dates(claim_text)
    evidence_dates = _extract_dates(evidence_text)
    if not claim_dates or not evidence_dates:
        return False
    return not any(
        _same_date(left, right) for left in claim_dates for right in evidence_dates
    )


def _strip_dates(text: str) -> str:
    for pattern in (_DATE_RE, _PT_DAY_DATE_RE, _PT_MONTH_DATE_RE, _SLASH_DATE_RE):
        text = pattern.sub(" ", text)
    return text


_FACT_TOKEN_RE = re.compile(
    r"(?<![\w-])[-+]?\d+(?:[.,]\d+)*(?:\s*%)?|[\wÀ-ÿ]+",
    re.UNICODE,
)
# Currency symbols are rewritten to ISO codes before tokenization so that
# "R$ 10", "US$ 10", "$10" and "10 USD" share one representation.
_CURRENCY_SYMBOLS = (
    (re.compile(r"R\$"), " brl "),
    (re.compile(r"US\$"), " usd "),
    (re.compile(r"\$"), " usd "),
    (re.compile(r"€"), " eur "),
)
_CURRENCIES = frozenset({"usd", "eur", "brl"})
_SCALES: dict[str, tuple[str, Decimal]] = {
    "thousand": ("thousand", Decimal(10) ** 3),
    "mil": ("thousand", Decimal(10) ** 3),
    "million": ("million", Decimal(10) ** 6),
    "millions": ("million", Decimal(10) ** 6),
    "milhão": ("million", Decimal(10) ** 6),
    "milhao": ("million", Decimal(10) ** 6),
    "milhões": ("million", Decimal(10) ** 6),
    "milhoes": ("million", Decimal(10) ** 6),
    "billion": ("billion", Decimal(10) ** 9),
    "billions": ("billion", Decimal(10) ** 9),
    "bilhão": ("billion", Decimal(10) ** 9),
    "bilhao": ("billion", Decimal(10) ** 9),
    "bilhões": ("billion", Decimal(10) ** 9),
    "bilhoes": ("billion", Decimal(10) ** 9),
}
_SCALE_FACTORS = {"base": Decimal(1), **{name: factor for name, factor in _SCALES.values()}}
_CONNECTORS = frozenset({"de", "of", "em", "in"})
_MILLISECOND_WORDS = frozenset(
    {"ms", "millisecond", "milliseconds", "milissegundo", "milissegundos"}
)
_PERCENT_WORDS = frozenset({"percent", "porcento", "pct"})
_COUNT_NOUNS: dict[str, str] = {
    "employees": "employees",
    "funcionários": "employees",
    "funcionarios": "employees",
    "colaboradores": "employees",
    "people": "people",
    "pessoas": "people",
    "customers": "customers",
    "clientes": "customers",
    "offices": "offices",
    "escritórios": "offices",
    "escritorios": "offices",
}
_ATTRIBUTE_ALIASES = {
    "receita": "revenue",
    "faturamento": "revenue",
    "revenue": "revenue",
    "lucro": "profit",
    "profit": "profit",
    "custo": "cost",
    "custos": "cost",
    "cost": "cost",
    "costs": "cost",
    "margem": "margin",
    "margin": "margin",
}
_YEAR_MIN = 1900
_YEAR_MAX = 2100


def _fact_tokens(text: str) -> list[str]:
    normalized = _strip_dates(text)
    for pattern, replacement in _CURRENCY_SYMBOLS:
        normalized = pattern.sub(replacement, normalized)
    return _FACT_TOKEN_RE.findall(normalized.casefold())


def _is_number(token: str) -> bool:
    return any(character.isdigit() for character in token)


def _currency_and_scale(tokens: list[str], index: int) -> tuple[str, str] | None:
    """Return (currency, scale) only when a currency is bound to this number.

    Accepted shapes: `USD 120 [million]` and `120 [million] [de|of] USD`.
    A currency elsewhere in the sentence never binds, so years and counts
    near a monetary value are not misread as money.
    """
    scale = "base"
    cursor = index + 1
    if cursor < len(tokens) and tokens[cursor] in _SCALES:
        scale = _SCALES[tokens[cursor]][0]
        cursor += 1
    if index > 0 and tokens[index - 1] in _CURRENCIES:
        return tokens[index - 1], scale
    if cursor < len(tokens) and tokens[cursor] in _CONNECTORS:
        cursor += 1
    if cursor < len(tokens) and tokens[cursor] in _CURRENCIES:
        return tokens[cursor], scale
    return None


def _attribute(tokens: list[str], index: int, entities: set[str]) -> str:
    """Nearest attribute alias in the clause, else nearest content word before."""
    for distance in range(1, 9):
        for position in (index - distance, index + distance):
            if 0 <= position < len(tokens) and tokens[position] in _ATTRIBUTE_ALIASES:
                return _ATTRIBUTE_ALIASES[tokens[position]]
    for position in range(index - 1, max(-1, index - 5), -1):
        value = tokens[position]
        if (
            not _is_number(value)
            and value not in _STOPWORDS
            and value not in _UNIT_WORDS
            and value not in _CURRENCIES
            and value not in _SCALES
            and value not in _CONNECTORS
            and value not in entities
        ):
            return value
    return "unknown"


def _numeric_facts(text: str) -> list[tuple[str, str, str]]:
    """Extract (raw value, unit, attribute) facts deterministically.

    `unit` is `currency:scale` for money, `percent`, `year`, `ms`,
    `count:<noun>` or `scalar`. Extraction never raises on free text.
    """
    tokens = _fact_tokens(text)
    entities = _entities(text)
    facts: list[tuple[str, str, str]] = []
    for index, token in enumerate(tokens):
        if not _is_number(token):
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        money = _currency_and_scale(tokens, index)
        if "%" in token or following in _PERCENT_WORDS or (
            following == "por" and index + 2 < len(tokens) and tokens[index + 2] == "cento"
        ):
            unit = "percent"
        elif money is not None:
            unit = f"{money[0]}:{money[1]}"
        elif following in _MILLISECOND_WORDS:
            unit = "ms"
        elif following in _COUNT_NOUNS:
            unit = f"count:{_COUNT_NOUNS[following]}"
        elif token.isdigit() and len(token) == 4 and _YEAR_MIN <= int(token) <= _YEAR_MAX:
            unit = "year"
        else:
            unit = "scalar"
        if unit == "year":
            attribute = "year"
        elif unit.startswith("count:"):
            attribute = unit.split(":", 1)[1]
        else:
            attribute = _attribute(tokens, index, entities)
        facts.append((token.replace(" ", ""), unit, attribute))
    return facts


def _locale_for(text: str) -> NumericLocale:
    return NumericLocale.PT_BR if detect_language(text) == "pt" else NumericLocale.EN_US


def _fact_value(raw: str, unit: str, locale: NumericLocale) -> Decimal | None:
    try:
        value = parse_number(raw, locale=locale)
    except (ValueError, ArithmeticError):
        return None
    if ":" in unit and not unit.startswith("count:"):
        value *= _SCALE_FACTORS.get(unit.split(":", 1)[1], Decimal(1))
    return value


def _comparable(left_unit: str, right_unit: str) -> bool:
    if left_unit == right_unit:
        return True
    left_money = left_unit.split(":", 1)[0] in _CURRENCIES
    right_money = right_unit.split(":", 1)[0] in _CURRENCIES
    return left_money and right_money and left_unit.split(":")[0] == right_unit.split(":")[0]


def _numeric_relation(claim_text: str, evidence_text: str) -> tuple[bool, bool]:
    conflict, agreement, _ = _numeric_facts_align(claim_text, evidence_text)
    return conflict, agreement


def _entities(text: str) -> set[str]:
    return {match.group("name").casefold() for match in _ENTITY_RE.finditer(text)}


def _numeric_facts_align(
    claim_text: str, evidence_text: str
) -> tuple[bool, bool, bool]:
    """Return (conflict, agreement, every_claim_fact_matched).

    Facts match only on equal attribute and comparable unit; `unknown`
    attributes never match, so an unverifiable number cannot yield SUPPORTS.
    Each side is parsed with the locale of its own text (pt-BR vs en-US).
    """
    claim_entities = _entities(claim_text)
    evidence_entities = _entities(evidence_text)
    if claim_entities and not claim_entities.intersection(evidence_entities):
        return False, False, False

    claim_facts = _numeric_facts(claim_text)
    if not claim_facts:
        return False, False, True
    evidence_facts = _numeric_facts(evidence_text)
    claim_locale = _locale_for(claim_text)
    evidence_locale = _locale_for(evidence_text)

    conflict = False
    agreement = False
    matched_claim_facts = 0
    for left, left_unit, left_attribute in claim_facts:
        left_value = _fact_value(left, left_unit, claim_locale)
        if left_value is None or left_attribute == "unknown":
            continue
        matches = [
            value
            for right, right_unit, right_attribute in evidence_facts
            if right_attribute == left_attribute and _comparable(left_unit, right_unit)
            for value in [_fact_value(right, right_unit, evidence_locale)]
            if value is not None
        ]
        if not matches:
            continue
        matched_claim_facts += 1
        # Calendar years are identifiers, not magnitudes: they must match exactly.
        tolerance = Decimal(0) if left_unit == "year" else DEFAULT_RELATIVE_TOLERANCE
        for right_value in matches:
            if relative_difference(left_value, right_value) > tolerance:
                conflict = True
            else:
                agreement = True

    return conflict, agreement, matched_claim_facts == len(claim_facts)


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
    version = "5"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        return _numeric_conflict(claim_text, evidence_text)

    @staticmethod
    def _date_conflict(claim_text: str, evidence_text: str) -> bool:
        return _dates_conflict(claim_text, evidence_text)

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
                claim_has_date = bool(_extract_dates(claim_item.claim.text))
                claim_entities = _entities(claim_item.claim.text)
                evidence_entities = _entities(item.excerpt)
                entity_mismatch = bool(
                    claim_entities and not claim_entities.intersection(evidence_entities)
                )
                date_conflict = self._date_conflict(claim_item.claim.text, item.excerpt)
                evidence_has_date = bool(_extract_dates(item.excerpt))
                negation_conflict = _has_negation(claim_item.claim.text) != _has_negation(
                    item.excerpt
                )
                direction_conflict = _direction_conflict(claim_item.claim.text, item.excerpt)
                unverified_structured_fact = (
                    (claim_has_numeric and (not numeric_matched or not numeric_agreement))
                    or (claim_has_date and not evidence_has_date)
                    or entity_mismatch
                )
                # Numeric conflicts are already gated by attribute/entity alignment.
                # Polarity and date mismatches only count when claim and evidence
                # describe the same proposition; otherwise they are unrelated text.
                same_proposition = lexical >= 0.25
                if numeric_conflict or (
                    same_proposition and (date_conflict or negation_conflict or direction_conflict)
                ):
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
                            _sha256(claim_item.claim.text + "\n" + item.excerpt),
                            _sha256(payload),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class NLIStanceDetector(StanceDetector):
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
                                claim_item.claim.text + "\n"
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
                if translated_document != document:
                    # Translation has no character alignment contract. Never expose
                    # translated-text offsets as if they were source-document offsets.
                    provenance_start = item.start_offset
                    provenance_end = item.end_offset
                    provenance_excerpt = document
                else:
                    provenance_start = start
                    provenance_end = end
                    local_start = start - temp_evidence.start_offset
                    local_end = end - temp_evidence.start_offset
                    provenance_excerpt = document[local_start:local_end]
                provenance_input = translated_claim + "\n" + provenance_excerpt
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
                            f"{self.version}|window={provenance_start}:{provenance_end}|"
                            f"translation={translation_hash}",
                            _sha256(provenance_input),
                            _sha256(
                                f"{stance}|{confidence:.12f}|{provenance_start}|"
                                f"{provenance_end}|{translation_hash}"
                            ),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))



def _sentence_windows(evidence: Evidence) -> list[tuple[int, int, str]]:
    text = evidence.excerpt
    spans: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"[.!?](?:[\"”’)]*)?(?=\s|$)", text):
        end = match.end()
        raw = text[start:end]
        left = start + len(raw) - len(raw.lstrip())
        right = start + len(raw.rstrip())
        if left < right:
            spans.append(
                (
                    evidence.start_offset + left,
                    evidence.start_offset + right,
                    text[left:right],
                )
            )
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text):
        spans.append((evidence.start_offset + start, evidence.end_offset, text[start:]))
    if not spans:
        spans.append((evidence.start_offset, evidence.end_offset, text))
    return spans


class SentenceNLIStanceDetector(NLIStanceDetector):
    """H1: evaluate claim against deterministic sentence spans."""

    component = "stance_detector.nli_sentence"

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        return _sentence_windows(evidence)


class SentenceTranslatedNLIStanceDetector(TranslatedNLIStanceDetector):
    """H1 translated path: sentence aggregation with the E1 translation contract."""

    component = "stance_detector.translate_nli_sentence"

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        return _sentence_windows(evidence)


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
