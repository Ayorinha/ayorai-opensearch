"""Field-by-field comparison of structured data against a document (deterministic).

Use case: a submitted record (for example, a protest remittance) states typed values
— amount, due date, CPF/CNPJ, names — and the document must be checked against them.
For each field the document is scanned for candidate values of the same type, with
exact character offsets; candidates next to one of the field's labels are preferred.

Outcomes per field:
- ``conforme``: a candidate equal to the expected value was found (near a label, when
  labels are given and a labelled candidate exists);
- ``divergente``: labelled candidates exist and none is equal — the document value is
  reported with its excerpt;
- ``ausente``: no candidate of that type (near a label, when labels are given); the
  system abstains rather than guess;
- ``ambiguo``: the field label introduces more than one distinct value (for example an
  original and a corrected amount); a person must decide;
- ``invalido``: the expected value itself is malformed (for example, a CPF/CNPJ with
  wrong check digits).

Labels match whole words; a value belongs to the nearest preceding label (no other value
of the same type in between), on its own line or on the line above. A text field with
labels is compared with the whole value the label introduces, never with a fragment of
it and never with the same name under another label (sacador versus sacado).

Normalisation is explicit and versioned; nothing is inferred by a model.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

FIELD_CHECK_VERSION = "field-check-2"
FIELD_TYPES = ("money", "date", "cpf_cnpj", "number", "text")
LABEL_WINDOW = 80  # characters before a candidate searched for a label

_MONEY_RE = re.compile(
    r"(?:R\$\s*)?(?<![\d.,])(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}|\d{1,3}(?:,\d{3})+\.\d{2}|\d+\.\d{2})(?![\d])"
    r"|R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?![\d.,]*\d)"
)
_DATE_RE = re.compile(
    r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?!\d)|(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)"
)
_DOC_RE = re.compile(
    r"(?<!\d)(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})(?!\d)"
)
_NUMBER_RE = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?(?![\d])")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str
    value: str
    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class Candidate:
    start: int
    end: int
    raw: str
    normalized: str
    labelled: bool


@dataclass(frozen=True)
class FieldResult:
    name: str
    type: str
    expected: str
    expected_normalized: str | None
    outcome: str
    found: str | None
    found_normalized: str | None
    start: int | None
    end: int | None
    excerpt: str | None
    reason: str


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_money(raw: str) -> str | None:
    value = raw.replace("R$", "").strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}", value):
        value = value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d{2}", value):
        value = value.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):  # 1.250 (Brazilian thousands)
        value = value.replace(".", "")
    elif not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None
    try:
        return f"{Decimal(value):.2f}"
    except InvalidOperation:
        return None


def normalize_date(raw: str) -> str | None:
    match = _DATE_RE.fullmatch(raw.strip())
    if not match:
        return None
    if match.group(1):
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    else:
        year, month, day = int(match.group(4)), int(match.group(5)), int(match.group(6))
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def cpf_cnpj_is_valid(digits: str) -> bool:
    if len(digits) == 11 and len(set(digits)) > 1:
        for size in (9, 10):
            total = sum(int(digits[i]) * (size + 1 - i) for i in range(size))
            check = (total * 10) % 11 % 10
            if check != int(digits[size]):
                return False
        return True
    if len(digits) == 14 and len(set(digits)) > 1:
        weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for size in (12, 13):
            factors = weights if size == 12 else [6, *weights]
            total = sum(int(digits[i]) * factors[i] for i in range(size))
            remainder = total % 11
            check = 0 if remainder < 2 else 11 - remainder
            if check != int(digits[size]):
                return False
        return True
    return False


def normalize_cpf_cnpj(raw: str) -> str | None:
    digits = _digits(raw)
    return digits if len(digits) in (11, 14) else None


def normalize_number(raw: str) -> str | None:
    value = raw.strip().replace(",", ".")
    try:
        return format(Decimal(value).normalize(), "f")
    except InvalidOperation:
        return None


def normalize_text(raw: str) -> str:
    return " ".join(re.findall(r"\w+", _fold(raw)))


NORMALIZERS = {
    "money": normalize_money,
    "date": normalize_date,
    "cpf_cnpj": normalize_cpf_cnpj,
    "number": normalize_number,
}


_TEXT_STOP = re.compile(r"\s+-\s+|\s*\(|\s*;|\s+(?:CPF|CNPJ)\b|\s{2,}", re.IGNORECASE)


def _label_spans(text: str, labels: Sequence[str]) -> list[tuple[int, int, bool]]:
    """(start, end, followed_by_colon) of every whole-word label occurrence."""

    folded = _fold(text)  # same length as text for Latin script
    if len(folded) != len(text):
        return []
    spans: list[tuple[int, int, bool]] = []
    for label in labels:
        needle = _fold(label).strip()
        if not needle:
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", folded):
            after = text[match.end() : match.end() + 40].split("\n", 1)[0]
            spans.append((match.start(), match.end(), bool(re.match(r"[^:\n]{0,30}:", after))))
    return sorted(spans)


def _search_start(text: str, start: int) -> int:
    """Labels count on the candidate's line, or on the line above when the candidate
    starts its line (table and PDF layouts put the label above the value)."""

    line_start = text.rfind("\n", 0, start) + 1
    if text[line_start:start].strip() or line_start == 0:
        return max(line_start, start - LABEL_WINDOW)
    previous = text.rfind("\n", 0, line_start - 1) + 1
    return max(previous, start - LABEL_WINDOW)


def _mark_labelled(text: str, found: list[Candidate], labels: Sequence[str]) -> list[Candidate]:
    """A candidate is labelled when a label precedes it nearby and no other value of
    the same type sits between that label and the candidate (nearest-label rule)."""

    spans = _label_spans(text, labels)
    marked = []
    for item in found:
        lower = _search_start(text, item.start)
        labelled = False
        for _, label_end, _ in spans:
            if lower <= label_end <= item.start and not any(
                label_end <= other.start < item.start for other in found if other is not item
            ):
                labelled = True
                break
        marked.append(Candidate(item.start, item.end, item.raw, item.normalized, labelled))
    return marked


def candidates(text: str, spec: FieldSpec) -> list[Candidate]:
    found: list[Candidate] = []
    if spec.type == "text":
        expected = normalize_text(spec.value)
        if not expected:
            return []
        folded_tokens = [
            (match.start(), match.end(), _fold(match.group()))
            for match in re.finditer(r"\w+", text)
        ]
        size = len(expected.split())
        for index in range(len(folded_tokens) - size + 1):
            window = folded_tokens[index : index + size]
            if " ".join(token for _, _, token in window) == expected:
                start, end = window[0][0], window[-1][1]
                found.append(Candidate(start, end, text[start:end], expected, False))
        return found
    pattern = {"money": _MONEY_RE, "date": _DATE_RE, "cpf_cnpj": _DOC_RE, "number": _NUMBER_RE}[
        spec.type
    ]
    normalizer = NORMALIZERS[spec.type]
    for match in pattern.finditer(text):
        group = (1 if match.group(1) else 2) if spec.type == "money" else 0
        raw = match.group(group)
        start, end = match.start(group), match.end(group)
        normalized = normalizer(raw)
        if normalized is not None:
            found.append(Candidate(start, end, raw, normalized, False))
    return _mark_labelled(text, found, spec.labels) if spec.labels else found


def labelled_text_values(text: str, labels: Sequence[str]) -> list[tuple[int, int, str, bool]]:
    """The text value introduced by each label: from the label (after a colon, when
    there is one) to the end of the line or the next separator."""

    values = []
    for _, label_end, has_colon in _label_spans(text, labels):
        line_end = text.find("\n", label_end)
        line_end = len(text) if line_end == -1 else line_end
        start = label_end
        if has_colon:
            start = text.index(":", label_end) + 1
        segment = text[start:line_end]
        stop = _TEXT_STOP.search(segment)
        if stop:
            segment = segment[: stop.start()]
        stripped = segment.strip().rstrip(".,")
        if not stripped:
            continue
        offset = start + segment.index(stripped)
        values.append((offset, offset + len(stripped), stripped, has_colon))
    return values


def _excerpt(text: str, start: int, end: int) -> tuple[int, int, str]:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end
    return line_start, line_end, text[line_start:line_end].strip()


def _result(
    spec: FieldSpec,
    expected: str | None,
    outcome: str,
    reason: str,
    text: str = "",
    hit: tuple[int, int, str, str] | None = None,
) -> FieldResult:
    start = end = None
    found = found_normalized = excerpt = None
    if hit is not None:
        start, end, found, found_normalized = hit
        excerpt = _excerpt(text, start, end)[2]
    return FieldResult(
        name=spec.name,
        type=spec.type,
        expected=spec.value,
        expected_normalized=expected,
        outcome=outcome,
        found=found,
        found_normalized=found_normalized,
        start=start,
        end=end,
        excerpt=excerpt,
        reason=reason,
    )


def _check_text(text: str, spec: FieldSpec, expected: str) -> FieldResult:
    if not spec.labels:
        found = candidates(text, spec)
        if found:
            first = found[0]
            return _result(
                spec,
                expected,
                "conforme",
                "equal text found (no label given)",
                text,
                (first.start, first.end, first.raw, first.normalized),
            )
        return _result(spec, expected, "ausente", "the expected text does not appear")
    values = labelled_text_values(text, spec.labels)
    if not values:
        return _result(spec, expected, "ausente", "no value next to the field label")
    matches = []
    for start, end, value, has_colon in values:
        normalized = normalize_text(value)
        # After "Label:" the whole value must be equal; in running text ("endosso ao
        # Banco Beta S.A.") the value must end with the expected name.
        equal = normalized == expected or (
            not has_colon and (" " + normalized).endswith(" " + expected)
        )
        matches.append((equal, (start, end, value, normalized)))
    distinct = {hit[3] for equal, hit in matches if not equal}
    if any(equal for equal, _ in matches):
        if distinct:
            hit = next(hit for equal, hit in matches if not equal)
            return _result(
                spec,
                expected,
                "ambiguo",
                "the field label introduces different values; a person must decide",
                text,
                hit,
            )
        hit = next(hit for equal, hit in matches if equal)
        return _result(spec, expected, "conforme", "equal value next to a field label", text, hit)
    return _result(
        spec,
        expected,
        "divergente",
        "a different value appears next to the field label",
        text,
        matches[0][1],
    )


def check_field(text: str, spec: FieldSpec) -> FieldResult:
    if spec.type not in FIELD_TYPES:
        raise ValueError(f"unsupported field type {spec.type!r}")
    expected = (
        normalize_text(spec.value) if spec.type == "text" else NORMALIZERS[spec.type](spec.value)
    )
    if not expected or (spec.type == "cpf_cnpj" and not cpf_cnpj_is_valid(expected)):
        return _result(
            spec,
            expected or None,
            "invalido",
            "the expected value is malformed or has invalid check digits",
        )
    if spec.type == "text":
        return _check_text(text, spec, expected)
    found = candidates(text, spec)
    pool = [item for item in found if item.labelled] if spec.labels else found
    if not pool:
        return _result(
            spec,
            expected,
            "ausente",
            "no value of this type next to the field label"
            if spec.labels
            else "the expected value does not appear in the document",
        )
    if not spec.labels:
        match = next((item for item in pool if item.normalized == expected), None)
        if match is None:
            return _result(spec, expected, "ausente", "the expected value does not appear")
        return _result(
            spec,
            expected,
            "conforme",
            "equal value found (no label given)",
            text,
            (match.start, match.end, match.raw, match.normalized),
        )
    values = {item.normalized for item in pool}
    if len(values) > 1:
        other = next(item for item in pool if item.normalized != expected)
        return _result(
            spec,
            expected,
            "ambiguo",
            "the field label introduces different values; a person must decide",
            text,
            (other.start, other.end, other.raw, other.normalized),
        )
    item = pool[0]
    outcome = "conforme" if item.normalized == expected else "divergente"
    reason = (
        "equal value next to a field label"
        if outcome == "conforme"
        else "a different value appears next to the field label"
    )
    return _result(
        spec, expected, outcome, reason, text, (item.start, item.end, item.raw, item.normalized)
    )


def check_fields(text: str, specs: Sequence[FieldSpec]) -> list[FieldResult]:
    return [check_field(text, spec) for spec in specs]
