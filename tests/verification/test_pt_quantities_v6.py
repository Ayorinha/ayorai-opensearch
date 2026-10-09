"""Adversarial tests for rule stance v6: Portuguese quantities and named actors.

All sentences are new; none is taken from Golden sets or from the PT-CP-Audit
simulation cases.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.pt_normalize import (
    extract_quantities,
    named_entities,
    normalize_numerals,
)
from ayorai_attractor.verification.stance import RuleStanceDetector, _has_negation


def _stance(claim: str, evidence: str) -> Stance:
    extracted = ExtractedClaim(
        claim=Claim(id="c1", text=claim),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fixture", "1", "in", "out"),
    )
    item = Evidence(
        id="e1",
        claim_id="c1",
        source_id="e1",
        source_location="fixture://e1",
        retrieved_at=datetime(2026, 10, 9, tzinfo=UTC),
        start_offset=0,
        end_offset=len(evidence),
        excerpt=evidence,
        origin_id="o1",
    )
    return RuleStanceDetector().detect([extracted], [item]).edges[0].edge.stance


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("O mandato é de 4 (quatro) anos.", "O mandato é de 4 anos."),
        ("prazo de vinte e cinco dias", "prazo de 25 dias"),
        ("até trezentos e sessenta unidades", "até 360 unidades"),
        ("inferior a um ano", "inferior a 1 ano"),
        ("um servidor e uma servidora", "um servidor e uma servidora"),
        ("taxa de 12 por cento", "taxa de 12 por cento"),
        ("cento e vinte vagas", "120 vagas"),
    ],
)
def test_normalize_numerals(text: str, expected: str) -> None:
    assert normalize_numerals(text) == expected


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("cumprido mais de um terço do contrato", ["1/3"]),
        ("reduzida de um a dois terços", ["1/3", "2/3"]),
        ("ao menos metade dos votos", ["1/2"]),
        ("um quinto das vagas", ["1/5"]),
        ("até o dobro do valor", ["2"]),
        ("até o triplo do valor", ["3"]),
    ],
)
def test_extract_quantities(text: str, values: list[str]) -> None:
    facts, _ = extract_quantities(text)
    assert [value for value, _, _ in facts] == values


def test_comparative_bound_is_not_negation() -> None:
    assert not _has_negation("O contrato não pode ser superior a 5 anos.")
    assert not _has_negation("A tarifa não excede o teto e nem superior ao índice será.")
    assert _has_negation("A agência não renovou o contrato.")


def test_named_entities_ignore_leading_function_words() -> None:
    assert named_entities("Pela Agência Estadual de Águas foi emitida a nota.") == {
        "agencia estadual de aguas"
    }
    assert named_entities("A obra começou ontem.") == set()


@pytest.mark.parametrize(
    ("claim", "evidence", "expected"),
    [
        # number words vs digits
        (
            "O mandato do conselho tarifário dura quatro anos.",
            "O mandato do conselho tarifário é de 4 (quatro) anos.",
            Stance.SUPPORTS,
        ),
        (
            "O mandato do conselho tarifário dura seis anos.",
            "O mandato do conselho tarifário é de 4 (quatro) anos.",
            Stance.CONTRADICTS,
        ),
        # duration families convert
        (
            "O prazo de adaptação das concessionárias é de um ano.",
            "O prazo de adaptação das concessionárias é de 12 (doze) meses.",
            Stance.SUPPORTS,
        ),
        (
            "O prazo de adaptação das concessionárias é de dois anos.",
            "O prazo de adaptação das concessionárias é de 12 (doze) meses.",
            Stance.CONTRADICTS,
        ),
        # fractions and multipliers
        (
            "A progressão exige o cumprimento de um quarto do contrato de gestão.",
            "A progressão exige o cumprimento de um terço do contrato de gestão.",
            Stance.CONTRADICTS,
        ),
        (
            "A penalidade contratual pode chegar ao dobro do valor do serviço.",
            "A penalidade contratual pode chegar ao triplo do valor do serviço.",
            Stance.CONTRADICTS,
        ),
        (
            "A penalidade contratual pode chegar ao triplo do valor do serviço.",
            "A penalidade contratual pode chegar ao triplo do valor do serviço.",
            Stance.SUPPORTS,
        ),
        # measures
        (
            "A multa diária pode chegar a dez vezes o valor da tarifa.",
            "A multa diária não pode ser superior a 5 (cinco) vezes o valor da tarifa.",
            Stance.CONTRADICTS,
        ),
        # bound vs negation
        (
            "A concessão tem duração de até trinta anos.",
            "A concessão não pode ter duração superior a 30 (trinta) anos.",
            Stance.SUPPORTS,
        ),
        # competing named actor
        (
            "A fiscalização dos contratos cabe à Controladoria Geral do Município.",
            "A fiscalização dos contratos cabe ao Tribunal de Contas do Estado.",
            Stance.NEUTRAL,
        ),
        (
            "A fiscalização dos contratos cabe ao Tribunal de Contas do Estado.",
            "Compete ao Tribunal de Contas do Estado a fiscalização dos contratos.",
            Stance.SUPPORTS,
        ),
    ],
)
def test_v6_stance(claim: str, evidence: str, expected: Stance) -> None:
    assert _stance(claim, evidence) is expected


def test_generic_units_need_shared_proposition() -> None:
    # Same duration, unrelated subject: a number alone must not support or contradict.
    claim = "A licença-maternidade das servidoras municipais é de seis meses."
    evidence = "O prazo de recurso administrativo contra a multa de trânsito é de 6 (seis) meses."
    assert _stance(claim, evidence) is Stance.NEUTRAL
    claim = "A licença-maternidade das servidoras municipais é de quatro meses."
    assert _stance(claim, evidence) is Stance.NEUTRAL


def test_bare_number_cannot_support_alone() -> None:
    claim = "O recurso deve ser apresentado em 15 dias."
    evidence = "A comissão terá 15 membros titulares."
    assert _stance(claim, evidence) is not Stance.SUPPORTS
