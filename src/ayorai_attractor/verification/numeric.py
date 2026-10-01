"""Deterministic numeric and date comparison rules from ADR-002 §7."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class NumericLocale(StrEnum):
    EN_US = "en-US"
    PT_BR = "pt-BR"


DEFAULT_LOCALE = NumericLocale.EN_US
DEFAULT_RELATIVE_TOLERANCE = Decimal("0.01")
ZERO_THRESHOLD = Decimal("1e-9")


def parse_number(
    value: str,
    *,
    locale: NumericLocale | str = DEFAULT_LOCALE,
) -> Decimal:
    """Parse a numeric value using the locale of its source document.

    The locale, not visual formatting, determines decimal and thousands
    separators. Percent signs are accepted and do not change the numeric
    magnitude; callers comparing values should use the same attribute/unit.
    """
    text = value.strip()
    if not text:
        raise ValueError("numeric value must not be empty")

    selected = NumericLocale(locale)
    if text.endswith("%"):
        text = text[:-1].strip()
    if not text:
        raise ValueError("numeric value must contain digits")

    if selected is NumericLocale.EN_US:
        if "," in text and "." in text:
            if text.rfind(".") < text.rfind(","):
                raise ValueError("numeric separators do not match en-US locale")
            text = text.replace(",", "")
        elif "," in text:
            if not re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+", text):
                raise ValueError("ambiguous numeric formatting for en-US locale")
            text = text.replace(",", "")
    else:
        if "." in text and "," in text:
            if text.rfind(",") < text.rfind("."):
                raise ValueError("numeric separators do not match pt-BR locale")
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            if not re.fullmatch(r"[+-]?\d+(?:,\d+)", text):
                raise ValueError("ambiguous numeric formatting for pt-BR locale")
            text = text.replace(",", ".")
        elif "." in text:
            if re.fullmatch(r"[+-]?\d{1,3}(?:\.\d{3})+", text):
                text = text.replace(".", "")
            elif re.fullmatch(r"[+-]?\d{1,3}\.\d{2}", text):
                raise ValueError("ambiguous numeric formatting for pt-BR locale")
            elif not re.fullmatch(r"[+-]?\d+\.\d+", text):
                raise ValueError("ambiguous numeric formatting for pt-BR locale")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("invalid numeric value") from exc


def relative_difference(left: Decimal, right: Decimal) -> Decimal:
    """Return ADR-002 relative difference with exact equality near zero."""
    denominator = max(abs(left), abs(right))
    if denominator < ZERO_THRESHOLD:
        return Decimal(0)
    return abs(left - right) / denominator


def numeric_conflicts(
    left: str,
    right: str,
    *,
    locale: NumericLocale | str = DEFAULT_LOCALE,
    tolerance: Decimal = DEFAULT_RELATIVE_TOLERANCE,
) -> bool:
    """Return True only when two same-attribute values exceed the tolerance."""
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    left_value = parse_number(left, locale=locale)
    right_value = parse_number(right, locale=locale)
    return relative_difference(left_value, right_value) > tolerance


class DateGranularity(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


def parse_date(value: str, granularity: DateGranularity | str) -> date:
    """Parse an ISO date according to the precision asserted by the claim."""
    selected = DateGranularity(granularity)
    text = value.strip()
    try:
        if selected is DateGranularity.DAY:
            return date.fromisoformat(text)
        if selected is DateGranularity.MONTH:
            year, month = text.split("-")
            return date(int(year), int(month), 1)
        year = int(text)
        return date(year, 1, 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {selected.value}-granularity date: {value!r}") from exc


def dates_conflict(
    left: str,
    right: str,
    *,
    granularity: DateGranularity | str,
) -> bool:
    """Return True when dates differ at the granularity asserted by the claim."""
    selected = DateGranularity(granularity)
    left_date = parse_date(left, selected)
    right_date = parse_date(right, selected)
    if selected is DateGranularity.DAY:
        return left_date != right_date
    if selected is DateGranularity.MONTH:
        return (left_date.year, left_date.month) != (right_date.year, right_date.month)
    return left_date.year != right_date.year
