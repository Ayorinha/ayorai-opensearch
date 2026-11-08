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
- ``invalido``: the expected value itself is malformed (for example, a CPF/CNPJ with
  wrong check digits).

Normalisation is explicit and versioned; nothing is inferred by a model.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

FIELD_CHECK_VERSION = "field-check-1"
FIELD_TYPES = ("money", "date", "cpf_cnpj", "number", "text")
LABEL_WINDOW = 80  # characters before a candidate searched for a label

_MONEY_RE = re.compile(
    r"(?:R\$\s*)?(?<![\d.,])(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}|\d{1,3}(?:,\d{3})+\.\d{2}|\d+\.\d{2})(?![\d])"
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


def _labelled(text: str, start: int, labels: Sequence[str]) -> bool:
    if not labels:
        return False
    line_start = text.rfind("\n", 0, start) + 1
    window = _fold(text[max(line_start, start - LABEL_WINDOW) : start])
    return any(
        re.search(r"(?<!\w)" + re.escape(_fold(label)) + r"(?!\w)", window) for label in labels
    )


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
                found.append(
                    Candidate(
                        start, end, text[start:end], expected, _labelled(text, start, spec.labels)
                    )
                )
        return found
    pattern = {"money": _MONEY_RE, "date": _DATE_RE, "cpf_cnpj": _DOC_RE, "number": _NUMBER_RE}[
        spec.type
    ]
    normalizer = NORMALIZERS[spec.type]
    for match in pattern.finditer(text):
        group = 1 if spec.type == "money" else 0
        raw = match.group(group)
        start, end = match.start(group), match.end(group)
        normalized = normalizer(raw)
        if normalized is not None:
            found.append(
                Candidate(start, end, raw, normalized, _labelled(text, start, spec.labels))
            )
    return found


def _excerpt(text: str, start: int, end: int) -> tuple[int, int, str]:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end
    return line_start, line_end, text[line_start:line_end].strip()


def check_field(text: str, spec: FieldSpec) -> FieldResult:
    if spec.type not in FIELD_TYPES:
        raise ValueError(f"unsupported field type {spec.type!r}")
    expected = (
        normalize_text(spec.value) if spec.type == "text" else NORMALIZERS[spec.type](spec.value)
    )
    base = {"name": spec.name, "type": spec.type, "expected": spec.value}
    if not expected or (spec.type == "cpf_cnpj" and not cpf_cnpj_is_valid(expected)):
        return FieldResult(
            **base,
            expected_normalized=expected or None,
            outcome="invalido",
            found=None,
            found_normalized=None,
            start=None,
            end=None,
            excerpt=None,
            reason="the expected value is malformed or has invalid check digits",
        )
    found = candidates(text, spec)
    labelled = [item for item in found if item.labelled]
    pool = labelled if spec.labels and labelled else ([] if spec.labels else found)
    if spec.type == "text" and found and not pool:
        pool = found  # exact multi-word text match is meaningful even without a label
    match = next((item for item in pool if item.normalized == expected), None)
    if match is not None:
        _, _, excerpt = _excerpt(text, match.start, match.end)
        return FieldResult(
            **base,
            expected_normalized=expected,
            outcome="conforme",
            found=match.raw,
            found_normalized=match.normalized,
            start=match.start,
            end=match.end,
            excerpt=excerpt,
            reason="equal value found" + (" next to a field label" if match.labelled else ""),
        )
    if labelled and spec.type != "text":
        other = labelled[0]
        _, _, excerpt = _excerpt(text, other.start, other.end)
        return FieldResult(
            **base,
            expected_normalized=expected,
            outcome="divergente",
            found=other.raw,
            found_normalized=other.normalized,
            start=other.start,
            end=other.end,
            excerpt=excerpt,
            reason="a different value appears next to the field label",
        )
    return FieldResult(
        **base,
        expected_normalized=expected,
        outcome="ausente",
        found=None,
        found_normalized=None,
        start=None,
        end=None,
        excerpt=None,
        reason=(
            "no value of this type next to the field label"
            if spec.labels
            else "the expected value does not appear in the document"
        ),
    )


def check_fields(text: str, specs: Sequence[FieldSpec]) -> list[FieldResult]:
    return [check_field(text, spec) for spec in specs]
