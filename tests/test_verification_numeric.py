from decimal import Decimal

import pytest

from ayorai_attractor.verification.numeric import (
    DateGranularity,
    NumericLocale,
    dates_conflict,
    numeric_conflicts,
    parse_number,
    relative_difference,
)


def test_en_us_decimal_percent_values_are_equal() -> None:
    assert parse_number("3.1%", locale=NumericLocale.EN_US) == Decimal("3.1")
    assert not numeric_conflicts("3.1%", "3.10%", locale=NumericLocale.EN_US)


def test_en_us_thousands_values_within_tolerance() -> None:
    assert parse_number("1.000", locale=NumericLocale.EN_US) == Decimal("1.000")
    assert parse_number("1.004", locale=NumericLocale.EN_US) == Decimal("1.004")
    assert relative_difference(Decimal("1.000"), Decimal("1.004")) < Decimal("0.01")
    assert not numeric_conflicts("1.000", "1.004", locale=NumericLocale.EN_US)


def test_en_us_values_above_tolerance_conflict() -> None:
    assert numeric_conflicts("1.000", "1.020", locale=NumericLocale.EN_US)


def test_zero_values_use_exact_equality() -> None:
    assert relative_difference(Decimal("0"), Decimal("0")) == Decimal("0")
    assert relative_difference(Decimal("0"), Decimal("0.000000001")) == Decimal("0")


def test_locale_controls_interpretation() -> None:
    assert parse_number("1.000", locale=NumericLocale.EN_US) == Decimal("1.000")
    assert parse_number("1.000", locale=NumericLocale.PT_BR) == Decimal("1000")


@pytest.mark.parametrize(
    ("value", "locale"),
    [
        ("1,00", NumericLocale.EN_US),
        ("1.00", NumericLocale.PT_BR),
        ("1,00,000", NumericLocale.EN_US),
    ],
)
def test_reject_ambiguous_locale_formatting(value: str, locale: NumericLocale) -> None:
    with pytest.raises(ValueError):
        parse_number(value, locale=locale)


def test_day_granularity_conflicts_on_different_days() -> None:
    assert dates_conflict("2026-10-01", "2026-10-02", granularity=DateGranularity.DAY)


def test_month_granularity_ignores_day() -> None:
    assert not dates_conflict("2026-10", "2026-10", granularity=DateGranularity.MONTH)
    assert dates_conflict("2026-10", "2026-11", granularity=DateGranularity.MONTH)


def test_year_granularity_ignores_month() -> None:
    assert not dates_conflict("2026", "2026", granularity=DateGranularity.YEAR)
    assert dates_conflict("2026", "2027", granularity=DateGranularity.YEAR)


def test_date_precision_must_match_claim_granularity() -> None:
    with pytest.raises(ValueError):
        dates_conflict("2026-10-01", "2026-10", granularity=DateGranularity.DAY)
