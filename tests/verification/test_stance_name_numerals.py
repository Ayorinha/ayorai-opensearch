"""A numeral that belongs to a proper name is not a quantity or a year (defect P8).

"Três" in "Holding Três Rios" was rewritten as the digit 3 and extracted as a
quantity. For the another-period rule of detector v14 that quantity was a typed
fact, so a founding date contradicted by another year ("registrada em 2002" vs
"em 2006") abstained instead of refuting. A digit inside a name ("Construtora
2000") was read as a calendar year in the same way.

A numeral belongs to a name when it is written inside a run of capitalized
words: a capitalized number word next to another capitalized word, or a digit
right after a capitalized word that does not open the sentence and is not
followed by a unit, scale, currency or percent. Such a numeral becomes a name
identifier: it must be present in the evidence for a numeric match, but it never
supports, contradicts or sets a period on its own.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.stance import _numeric_facts


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


def _abstains(result: dict[str, object]) -> bool:
    return result["verdict"] is None and result["abstention_reason"] == "insufficient_evidence"


def _units(text: str) -> list[tuple[str, str]]:
    return [(value, unit) for value, unit, _ in _numeric_facts(text)]


TRES_REVENUE = "A receita da Holding Três Rios foi de 40 milhões em 2024."
C2000_REVENUE = "A receita da Construtora 2000 foi de 40 milhões em 2024."


# --- P8-A: a number word inside a name --------------------------------------------------


def test_p8a_number_word_in_a_name_is_a_name_identifier() -> None:
    facts = _units("A Holding Três Rios foi registrada na junta comercial em 2002.")
    assert facts == [("3", "name"), ("2002", "year")]


def test_p8a_the_founding_date_is_refuted_again() -> None:
    # The battery case: main refuted it, detector v14 abstained.
    result = _check(
        "A Holding Três Rios foi registrada na junta comercial em 2002.",
        "Registros indicam que a Holding Três Rios foi registrada na junta comercial em 2006.",
    )
    assert result["verdict"] == "refuted"
    assert [item["stance"] for item in result["evidence"]] == ["contradicts"]


def test_p8a_a_name_that_opens_the_sentence() -> None:
    assert _units("Três Rios foi emancipada em 1938.") == [("3", "name"), ("1938", "year")]
    assert (
        _check("Três Rios foi emancipada em 1938.", "Três Rios foi emancipada em 1941.")["verdict"]
        == "refuted"
    )


def test_p8a_a_number_word_outside_a_name_is_still_a_quantity() -> None:
    # Sentence-initial capital followed by a common noun: a count, not a name.
    assert ("3", "name") not in _units("Três empresas abriram filiais em 2024.")
    assert ("3", "name") not in _units("A Vértice abriu três lojas em 2024.")
    assert (
        _check("A Vértice abriu três lojas em 2024.", "A Vértice abriu cinco lojas em 2024.")[
            "verdict"
        ]
        == "refuted"
    )


# --- P8-B: digits inside a name ---------------------------------------------------------


def test_p8b_digits_in_a_name_are_not_a_year() -> None:
    assert _units(C2000_REVENUE) == [("2000", "name"), ("40", "scaled:million"), ("2024", "year")]


def test_p8b_the_same_fact_in_another_year_abstains() -> None:
    # The name's 2000 is not a period, so the evidence names only another year.
    assert _abstains(
        _check(C2000_REVENUE, "A receita da Construtora 2000 foi de 40 milhões em 2023.")
    )


def test_p8b_a_founding_date_with_digits_in_the_name() -> None:
    claim = "A Construtora 2000 foi fundada em 1998."
    assert _check(claim, "A Construtora 2000 foi fundada em 1998 em Curitiba.")["verdict"] == (
        "partially_supported"
    )
    assert _check(claim, "A Construtora 2000 foi fundada em 2001.")["verdict"] == "refuted"


@pytest.mark.parametrize(
    "text",
    [
        "Revenue was USD 120 million in 2024.",  # an all-caps currency is not a name word
        "In March 2024 AtlasGrid had 800 employees.",  # a month is not a name word
        "A Vértice 40 milhões de receita teve em 2024.",  # a scale follows the number
        "Em 2024 a Vértice teve receita de 40 milhões.",  # the capital opens the sentence
        "A margem da Vértice foi de 12%.",
    ],
)
def test_p8b_quantities_and_years_next_to_capitals_are_not_names(text: str) -> None:
    assert all(unit != "name" for _, unit in _units(text))


# --- P8-C: names without numerals are unchanged ------------------------------------------


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (
            "Relatório: a receita da Holding Rios Claros foi de 40 milhões em 2024.",
            "partially_supported",
        ),
        (
            "Segundo o balanço, a receita da Holding Rios Claros foi de 55 milhões em 2024.",
            "refuted",
        ),
    ],
)
def test_p8c_names_without_numerals(document: str, expected: str) -> None:
    claim = "A receita da Holding Rios Claros foi de 40 milhões em 2024."
    assert all(unit != "name" for _, unit in _units(claim))
    assert _check(claim, document)["verdict"] == expected


# --- P8-D: a year tied to a fact is still a year -------------------------------------------


@pytest.mark.parametrize("claim", [TRES_REVENUE, C2000_REVENUE])
def test_p8d_the_factual_year_still_supports(claim: str) -> None:
    assert ("2024", "year") in _units(claim)
    assert _check(claim, f"Relatório anual: {claim[0].lower()}{claim[1:]}")["verdict"] == (
        "partially_supported"
    )


# --- P8-E: genuine contradictions ----------------------------------------------------------


@pytest.mark.parametrize("claim", [TRES_REVENUE, C2000_REVENUE])
def test_p8e_same_attribute_same_year_other_value_refutes(claim: str) -> None:
    document = "Segundo o balanço auditado, " + claim[0].lower() + claim[1:].replace("40", "55")
    result = _check(claim, document)
    assert result["verdict"] == "refuted"
    assert [item["stance"] for item in result["evidence"]] == ["contradicts"]


# --- P8-F: revenue in one year, founding in another -----------------------------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (
            "A Holding Três Rios apresentou receita de R$ 40 milhões em 2024.",
            "A Holding Três Rios foi fundada em 1998.",
        ),
        (C2000_REVENUE, "A Construtora 2000 foi fundada em 1998 e tem sede em Joinville."),
        ("A Holding Três Rios foi fundada em 1998.", TRES_REVENUE),
    ],
)
def test_p8f_years_of_different_attributes_do_not_contradict(claim: str, document: str) -> None:
    assert _abstains(_check(claim, document))


# --- name identity: another numeral is another entity ---------------------------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (TRES_REVENUE, "A receita da Holding Quatro Rios foi de 40 milhões em 2024."),
        (TRES_REVENUE, "A receita da Holding Quatro Rios foi de 55 milhões em 2024."),
        (C2000_REVENUE, "A receita da Construtora 3000 foi de 40 milhões em 2024."),
        (
            "A Holding Três Rios tem sede em Curitiba.",
            "A Holding Quatro Rios tem sede em Curitiba.",
        ),
    ],
)
def test_a_different_numeral_in_the_name_neither_supports_nor_refutes(
    claim: str, document: str
) -> None:
    assert _abstains(_check(claim, document))


def test_a_claim_whose_only_numeral_is_in_the_name_is_still_supported() -> None:
    claim = "A Holding Três Rios tem sede em Curitiba."
    assert (
        _check(claim, "Segundo o cadastro, a Holding Três Rios tem sede em Curitiba.")["verdict"]
        == "partially_supported"
    )


# --- P8-H: name numeral, quantity and year in one claim -----------------------------------------


COMBINED = "A Holding Três Rios teve receita de R$ 40 milhões em 2024 com 3 fábricas."


def test_p8h_each_number_keeps_its_role() -> None:
    roles = _units(COMBINED)
    assert roles[0] == ("3", "name")
    assert ("40", "brl:million") in roles
    assert ("2024", "year") in roles
    assert sum(1 for value, unit in roles if value == "3" and unit != "name") == 1


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (
            "Segundo o balanço, a Holding Três Rios teve receita de R$ 40 milhões em 2024 "
            "com 3 fábricas.",
            "partially_supported",
        ),
        (
            "Segundo o balanço, a Holding Três Rios teve receita de R$ 55 milhões em 2024 "
            "com 3 fábricas.",
            "refuted",
        ),
        ("Segundo o balanço, a Holding Três Rios teve receita de R$ 40 milhões em 2023.", None),
        ("A Holding Três Rios foi fundada em 1998 e tem 3 fábricas.", None),
    ],
)
def test_p8h_combined_claim(document: str, expected: str | None) -> None:
    assert _check(COMBINED, document)["verdict"] == expected
