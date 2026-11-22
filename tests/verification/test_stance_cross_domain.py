"""Defects found by the cross-domain robustness battery (2026-11-22), detector v15.

Each group pins one root cause with the battery's phrasing, a second phrasing
written after the fix, and guard cases that must keep their previous verdict.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _has_negation,
    _numeric_facts,
    _shares_predicate,
)


def _verdict(claim: str, document: str) -> str | None:
    response = TestClient(app).post(
        "/v1/check", json={"claims": [claim], "documents": [{"id": "d0", "text": document}]}
    )
    assert response.status_code == 200
    verdict = response.json()["results"][0]["verdict"]
    assert verdict is None or isinstance(verdict, str)
    return verdict


P, R, U = "partially_supported", "refuted", None


# --- P1: units of one dimension are compared after normalization ----------------------------


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        (
            "A capacidade da Usina Campo Belo foi de 120 MW em 2024.",
            "A capacidade da Usina Campo Belo foi de 120 kW em 2024.",
            R,
        ),
        (
            "A extensão da Ferrovia Serra do Mar foi de 380 quilômetros em 1910.",
            "A extensão da Ferrovia Serra do Mar foi de 380 metros em 1910.",
            R,
        ),
        (
            "O prazo médio de entrega da Distribuidora Prata foi de 15 dias em 2024.",
            "O prazo médio de entrega da Distribuidora Prata foi de 15 horas em 2024.",
            R,
        ),
        (
            "O parque eólico Ventos do Norte tem 300 MW de capacidade.",
            "Com 300 MW de capacidade, o parque eólico Ventos do Norte entrou em operação.",
            P,
        ),
        (
            "A Agropecuária Boa Safra exportou 12 mil toneladas de soja em 2023.",
            "Em 2023, a Agropecuária Boa Safra exportou 18 mil toneladas de soja.",
            R,
        ),
    ],
)
def test_p1_units(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


def test_p1_units_are_typed() -> None:
    assert _numeric_facts("A capacidade foi de 120 MW.")[0][1] == "duration:power:1000000"
    assert _numeric_facts("15 dias")[0][1] == _numeric_facts("360 horas")[0][1].replace(":1", ":24")


def test_p1_segundo_is_not_a_unit() -> None:
    # "segundo" also means "according to": a year before it is still a year.
    claim = "A Clínica Bem Viver atendeu 8.500 pacientes em 2022."
    assert (
        _verdict(claim, "A Clínica Bem Viver atendeu 8.500 pacientes em 2022, segundo o balanço.")
        == P
    )


# --- P2: a value of another year's clause no longer supports --------------------------------


@pytest.mark.parametrize(
    ("claim", "document"),
    [
        (
            "O lucro líquido do Banco Horizonte foi de 120 milhões de reais em 2024.",
            "O lucro líquido do Banco Horizonte foi de 120 milhões de reais em 2023 "
            "e de 95 milhões de reais em 2024.",
        ),
        (
            "A população da Vila de São Bento foi de 3.200 habitantes em 1872.",
            "A população da Vila de São Bento foi de 3.200 habitantes em 1890 "
            "e de 4.100 habitantes em 1872.",
        ),
    ],
)
def test_p2_value_of_another_year_does_not_support(claim: str, document: str) -> None:
    # AP1: the claimed year's value is bound to the subject, so it now refutes.
    assert _verdict(claim, document) == R


@pytest.mark.parametrize(
    ("claim", "expected"),
    [("A receita foi de 40 milhões em 2024.", P), ("A receita foi de 35 milhões em 2023.", P)],
)
def test_p2_the_claimed_year_clause_still_supports(claim: str, expected: str) -> None:
    document = "A receita foi de 40 milhões em 2024 e de 35 milhões em 2023."
    assert _verdict(claim, document) == expected


def test_p2_respectively_is_left_alone() -> None:
    document = "As receitas de 2023 e 2024 foram de 35 e 40 milhões, respectivamente."
    assert _verdict("A receita foi de 40 milhões em 2024.", document) is None


# --- P3: Portuguese "no" is not English negation --------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["A Holding Rios investe no setor têxtil.", "O Shopping Center Norte fica no centro."],
)
def test_p3_pt_contraction_is_not_negation(text: str) -> None:
    assert _has_negation(text) is False


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        (
            "A participação acionária da Holding Rios foi de 34% em 2023.",
            "A Holding Rios investe no setor têxtil.",
            U,
        ),
        (
            "The Northwind Bank paid a dividend in 2024.",
            "The Northwind Bank paid no dividend in 2024.",
            R,
        ),
        ("The company had debt in 2024.", "The company had no debt in 2024.", R),
    ],
)
def test_p3_verdicts(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


# --- P4: another entity, a branch or a similar name neither confirms nor contradicts --------


@pytest.mark.parametrize(
    "document",
    [
        "O lucro do Banco Aurora foi de 95 milhões de reais em 2024.",
        "O lucro do Banco Horizonte Sul foi de 95 milhões de reais em 2024.",
        "O lucro da agência de Belém do Banco Horizonte foi de 95 milhões de reais em 2024.",
    ],
)
def test_p4_other_entity_abstains(document: str) -> None:
    assert (
        _verdict("O lucro do Banco Horizonte foi de 120 milhões de reais em 2024.", document)
        is None
    )


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        # The subunit noun belongs to another phrase: the bank itself is reported.
        (
            "O lucro do Banco Horizonte foi de 120 milhões em 2024.",
            "Com 300 agências, o lucro do Banco Horizonte foi de 95 milhões em 2024.",
            R,
        ),
        (
            "O lucro do Banco Horizonte foi de 120 milhões em 2024.",
            "Com 300 agências, o lucro do Banco Horizonte foi de 120 milhões em 2024.",
            P,
        ),
        # The claim is itself about the branch.
        (
            "A filial de Joinville do Banco Horizonte lucrou 10 milhões em 2024.",
            "A filial de Joinville do Banco Horizonte lucrou 12 milhões em 2024.",
            R,
        ),
        # A name that continues the claim's own name.
        (
            "A receita da Vértice Energia foi de 40 milhões em 2024.",
            "A receita da Vértice Energia foi de 55 milhões em 2024.",
            R,
        ),
        # "empresa não" is not an entity: a negation still contradicts.
        ("A empresa não tinha dívidas em 2024.", "A empresa tinha dívidas em 2024.", R),
    ],
)
def test_p4_guards(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


# --- P5: a passage that confirms one part of a compound claim does not refute it ------------


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        (
            "O lucro do Banco Horizonte foi de 120 milhões em 2024 "
            "e o Banco Horizonte foi fundado em 1987.",
            "O lucro do Banco Horizonte foi de 120 milhões em 2024.",
            U,
        ),
        (
            "A Clínica Bem Viver atendeu 8.500 pacientes em 2022 e foi inaugurada em 2009.",
            "A Clínica Bem Viver atendeu 8.500 pacientes em 2022.",
            U,
        ),
        # The passage names another year of its own: a real conflict.
        ("A Vértice foi fundada em 1998.", "A Vértice foi fundada em 2001.", R),
    ],
)
def test_p5_compound_claims(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


# --- P6: the type noun of a name is not a shared predicate ----------------------------------


@pytest.mark.parametrize(
    ("claim", "evidence", "expected"),
    [
        (
            "O município de Serra Alta foi emancipado em 1963.",
            "A população estimada do município de Serra Alta foi de 52 mil habitantes em 2024.",
            False,
        ),
        (
            "O estudo Coorte Aurora foi iniciado em 2015.",
            "A taxa de resposta do estudo Coorte Aurora foi de 62% em 2022.",
            False,
        ),
        (
            "O município de Serra Alta foi emancipado em 1963.",
            "O município de Serra Alta foi emancipado em 1968.",
            True,
        ),
    ],
)
def test_p6_type_nouns(claim: str, evidence: str, expected: bool) -> None:
    assert _shares_predicate(claim, evidence) is expected


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        (
            "O município de Serra Alta foi emancipado em 1963.",
            "A população estimada do município de Serra Alta foi de 52 mil habitantes em 2024.",
            U,
        ),
        (
            "O município de Lagoa Funda foi criado em 1958.",
            "O município de Lagoa Funda foi criado em 1962.",
            R,
        ),
        (
            "O estudo Coorte Aurora foi iniciado em 2015.",
            "O estudo Coorte Aurora foi iniciado em 2017.",
            R,
        ),
    ],
)
def test_p6_verdicts(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


# --- P7: years before 1900 are calendar years after a temporal preposition ------------------


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        ("A Vila de São Bento foi fundada em 1745.", "A Vila de São Bento foi fundada em 1752.", R),
        (
            "O Mosteiro de São Lourenço foi erguido em 1612.",
            "O Mosteiro de São Lourenço foi erguido em 1650.",
            R,
        ),
        ("A cidade foi fundada em 1554.", "A cidade foi fundada em 1554 por jesuítas.", P),
        (
            "A população da Vila de São Bento foi de 3.200 habitantes em 1872.",
            "A população da Vila de São Bento foi de 4.100 habitantes em 1890.",
            U,
        ),
        # A bare four-digit count is still a quantity.
        ("A biblioteca tem 1554 livros raros.", "A biblioteca tem 1600 livros raros.", R),
    ],
)
def test_p7_historical_years(claim: str, document: str, expected: str | None) -> None:
    assert _verdict(claim, document) == expected


def test_p7_bare_number_is_not_a_year() -> None:
    assert _numeric_facts("A vila tinha 1745 casas.")[0][1] != "year"
    assert _numeric_facts("A vila foi fundada em 1745.")[0][1] == "year"


def test_detector_version_is_15() -> None:
    assert RuleStanceDetector.version in {"15", "16"}


# --- AP1: the clause of another year keeps the subject when it opens the sentence ----------


@pytest.mark.parametrize(
    ("claim", "document", "expected"),
    [
        (
            "A receita da Vértice foi de 40 milhões em 2024.",
            "Em 2023, a receita da Vértice foi de 40 milhões; em 2024, de 55 milhões.",
            R,
        ),
        (
            "A receita da Vértice foi de 55 milhões em 2024.",
            "Em 2023, a receita da Vértice foi de 40 milhões; em 2024, de 55 milhões.",
            P,
        ),
        (
            "A receita da Vértice foi de 40 milhões em 2023.",
            "A receita da Vértice foi de 40 milhões em 2023 e de 55 milhões em 2024.",
            P,
        ),
    ],
)
def test_ap1_claimed_year_value_is_bound_to_the_subject(
    claim: str, document: str, expected: str | None
) -> None:
    assert _verdict(claim, document) == expected


def test_ap1_dropped_clause_keeps_no_year_of_its_own() -> None:
    from ayorai_attractor.verification.stance import _keep_claimed_period

    kept = _keep_claimed_period(
        "Em 2023, a receita foi de 40 milhões; em 2024, de 55 milhões.", {"2024"}
    )
    assert "2023" not in kept
    assert "40" not in kept
    assert "55" in kept and "receita" in kept
