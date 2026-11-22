"""A calendar year that belongs to another event must not refute a claim (POC case C2).

Before the fix, "A receita da Vértice foi de 40 milhões em 2024." checked against
"A Vértice foi fundada em 1998 e tem sede em Curitiba." was refuted: the claim's
"em 2024" and the founding year 1998 were compared as the same fact. A year only
contradicts when it is anchored to the claim's proposition: another claim fact
is compared in the same evidence, or the claim states only years and shares a
predicate word with the evidence.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _numeric_alignment,
    _shares_predicate,
)

REVENUE = "A receita da Vértice foi de 40 milhões em 2024."
FOUNDED = "A Vértice foi fundada em 1998."


def _check(claim: str, *documents: str) -> dict[str, object]:
    response = TestClient(app).post(
        "/v1/check",
        json={
            "claims": [claim],
            "documents": [{"id": f"d{i}", "text": text} for i, text in enumerate(documents)],
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert isinstance(result, dict)
    return result


# --- the defect: a year of another event is not a contradiction ------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (REVENUE, "A Vértice foi fundada em 1998 e tem sede em Curitiba."),  # POC case C2
        (FOUNDED, "A receita da Vértice foi de 40 milhões em 2024."),  # the mirror case
        (REVENUE, "A Vértice abriu sua filial em Curitiba em 2010."),  # another event's year
    ],
)
def test_a_year_of_another_event_abstains_instead_of_refuting(claim: str, document: str) -> None:
    result = _check(claim, document)
    assert result["verdict"] is None
    assert result["status"] == "abstain/no_answer"
    assert result["abstention_reason"] == "insufficient_evidence"
    assert not _numeric_alignment(claim, document).conflict


# --- real contradictions still refute ---------------------------------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (FOUNDED, "A Vértice foi fundada em 2001."),  # the year is the claimed fact
        (REVENUE, "Segundo o balanço auditado, a receita da Vértice foi de 55 milhões em 2024."),
        (REVENUE, "A receita da Vértice foi de 55 milhões."),
    ],
)
def test_real_contradictions_still_refute(claim: str, document: str) -> None:
    result = _check(claim, document)
    assert result["verdict"] == "refuted"
    assert [item["stance"] for item in result["evidence"]] == ["contradicts"]


# --- support, conflict and abstention are unchanged -------------------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (REVENUE, "Relatório anual: a receita da Vértice foi de 40 milhões em 2024."),
        (FOUNDED, "A Vértice foi fundada em 1998 e tem sede em Curitiba."),
        (
            "A Lei nº 14.063 foi publicada em 23 de setembro de 2020.",
            "A Lei nº 14.063 foi publicada em 23 de setembro de 2020 no Diário Oficial da União.",
        ),
    ],
)
def test_matching_years_still_support(claim: str, document: str) -> None:
    assert _check(claim, document)["verdict"] == "partially_supported"


@pytest.mark.parametrize(
    "document",
    [
        "A Vértice tem 40 funcionários e sede em Curitiba.",  # coincident number, other quantity
        "A Vértice abriu sua filial em Curitiba em 2024.",  # coincident year, other event
        "A Vértice tem sede em Curitiba e atua no setor de energia.",  # no number at all
    ],
)
def test_coincident_numbers_neither_support_nor_refute(document: str) -> None:
    result = _check(REVENUE, document)
    assert result["verdict"] is None
    assert result["abstention_reason"] == "insufficient_evidence"


def test_divergent_documents_are_still_conflicting() -> None:
    result = _check(
        REVENUE,
        "Relatório anual: a receita da Vértice foi de 40 milhões em 2024.",
        "Segundo reportagem, a receita da Vértice foi de 55 milhões em 2024.",
    )
    assert result["verdict"] == "conflicting"


# --- the predicate test -------------------------------------------------------------


@pytest.mark.parametrize(
    ("claim", "evidence", "expected"),
    [
        (FOUNDED, "A Vértice foi fundada em 2001.", True),  # shares "fundada"
        (FOUNDED, "A receita da Vértice foi de 40 milhões.", False),  # only the name is shared
        ("A Vértice foi fundada em 1998.", "Vértice, empresa de Curitiba.", False),
        ("Fundada em 1998, a Vértice cresceu.", "A Vértice foi fundada em 2001.", True),
        ("Vértice foi fundada em 1998.", "A receita da Vértice foi de 40 milhões.", False),
        ("A Vértice tem sede desde 1998.", "A Vértice tem 40 lojas.", False),
    ],
)
def test_shares_predicate_ignores_proper_nouns(claim: str, evidence: str, expected: bool) -> None:
    assert _shares_predicate(claim, evidence) is expected


# --- another period: the evidence describes a different year -----------------------


@pytest.mark.parametrize(
    "document",
    [
        "A receita da Vértice foi de 40 milhões em 2023.",  # same value, other year
        "A receita da Vértice foi de 55 milhões em 2023.",  # other value, other year
    ],
)
def test_the_same_fact_in_another_year_abstains(document: str) -> None:
    result = _check(REVENUE, document)
    assert result["verdict"] is None
    assert result["abstention_reason"] == "insufficient_evidence"


def test_the_claimed_year_among_others_still_decides() -> None:
    supported = _check(
        REVENUE, "A receita da Vértice foi de 31 milhões em 2023 e de 40 milhões em 2024."
    )
    assert supported["verdict"] == "partially_supported"
    assert (
        _check(REVENUE, "A receita da Vértice foi de 55 milhões em 2024.")["verdict"] == "refuted"
    )


def test_a_fact_without_a_year_in_the_evidence_is_still_compared() -> None:
    # No period in the evidence: the claimed value is compared as before.
    assert _check(REVENUE, "A receita da Vértice foi de 55 milhões.")["verdict"] == "refuted"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "known limitation, also on main: numbers are not bound to their own year inside a "
        "sentence, so 40 matches the 2023 value and the claim about 2024 is supported"
    ),
)
def test_a_value_of_another_year_in_the_same_sentence_does_not_support() -> None:
    result = _check(
        REVENUE, "A receita da Vértice foi de 40 milhões em 2023 e de 55 milhões em 2024."
    )
    assert result["verdict"] == "refuted"


# --- names that open a sentence and generic verbs are not predicates -------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        ("Vértice foi fundada em 1998.", "A receita da Vértice foi de 40 milhões em 2024."),
        (
            "A Vértice tem sede em Curitiba desde 1998.",
            "A Vértice tem 40 lojas e abriu a filial em 2010.",
        ),
    ],
)
def test_a_leading_name_or_a_generic_verb_does_not_anchor_a_year(claim: str, document: str) -> None:
    result = _check(claim, document)
    assert result["verdict"] is None
    assert result["abstention_reason"] == "insufficient_evidence"


def test_detector_version_is_14() -> None:
    assert RuleStanceDetector.version == "14"
