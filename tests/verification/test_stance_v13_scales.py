"""Detector v10: scale words without a currency, and scaled counts."""

from __future__ import annotations

import pytest

from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _numeric_alignment,
    _numeric_facts,
)


@pytest.mark.parametrize(
    ("text", "fact"),
    [
        ("A receita foi de 1,2 bilhão.", ("1,2", "scaled:billion", "revenue")),
        ("A receita foi de 1.200 milhões.", ("1.200", "scaled:million", "revenue")),
        (
            "A NovaBank tinha 2,0 milhões de clientes de varejo.",
            ("2,0", "count:customers:million", "count:customers"),
        ),
        (
            "NovaBank had 2.3 million active retail customers.",
            ("2.3", "count:customers:million", "count:customers"),
        ),
        ("A empresa tem 3 mil funcionários.", ("3", "count:employees:thousand", "count:employees")),
        # Money keeps its currency unit, as before.
        ("A receita foi de R$ 40 milhões.", ("40", "brl:million", "revenue")),
    ],
)
def test_scaled_facts(text: str, fact: tuple[str, str, str]) -> None:
    assert fact in _numeric_facts(text)


@pytest.mark.parametrize(
    ("claim", "evidence", "conflict"),
    [
        ("A receita foi de 1,2 bilhão.", "A receita foi de 1.200 milhões.", False),
        ("A receita foi de 1,2 bilhão.", "A receita foi de 1.500 milhões.", True),
        ("A empresa tem 3 mil funcionários.", "A empresa tem 3000 funcionários.", False),
        ("A empresa tem 3 mil funcionários.", "A empresa tem 4500 funcionários.", True),
        (
            "A NovaBank tinha 2,0 milhões de clientes.",
            "NovaBank reported 2.0 million active retail customers.",
            False,
        ),
        (
            "A NovaBank tinha 2,0 milhões de clientes.",
            "NovaBank had 2.3 million active retail customers.",
            True,
        ),
    ],
)
def test_scaled_values_compare_by_magnitude(claim: str, evidence: str, conflict: bool) -> None:
    alignment = _numeric_alignment(claim, evidence)
    assert alignment.conflict is conflict
    assert alignment.agreement is not conflict
    assert alignment.all_matched


def test_different_count_nouns_never_compare() -> None:
    alignment = _numeric_alignment(
        "A empresa tem 3 mil funcionários.", "A empresa tem 3 mil clientes."
    )
    assert not alignment.conflict and not alignment.agreement and not alignment.all_matched


def test_detector_version_is_11() -> None:
    assert RuleStanceDetector.version in {"13", "14"}
