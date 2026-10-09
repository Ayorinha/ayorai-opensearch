"""Adversarial tests for Portuguese rule-based stance.

These cases are written from scratch for the three defects below. None of them
is copied from or derived from the Golden evaluation sets.

1. "no"/"na"/"nos"/"nas" (em + article) and "sem" were read as negation.
2. Only ISO dates were recognised; Portuguese written and slash dates were not.
3. Opposite directional predicates ("subiu" x "caiu") with equal numbers were
   read as support.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.models import Claim, Evidence, Stance, Verdict
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _dates_conflict,
    _extract_dates,
    _has_negation,
)


def _claim(text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id="c1", text=text),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fixture", "1", "in", "out"),
    )


def _evidence(text: str) -> Evidence:
    return Evidence(
        id="e1",
        claim_id="c1",
        source_id="e1",
        source_location="fixture://e1",
        retrieved_at=datetime(2026, 10, 8, tzinfo=UTC),
        start_offset=0,
        end_offset=len(text),
        excerpt=text,
        origin_id="o1",
    )


def _stance(claim: str, evidence: str) -> Stance:
    result = RuleStanceDetector().detect([_claim(claim)], [_evidence(evidence)])
    return result.edges[0].edge.stance


def _verdict(claim: str, evidence: str) -> Verdict:
    extracted = _claim(claim)
    item = _evidence(evidence)
    edges = RuleStanceDetector().detect([extracted], [item]).edges
    _, verdict = judge([extracted.claim], [item], [edge.edge for edge in edges])
    return verdict


# --- 1. Language-dependent negation -------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "A cooperativa Serrana tinha 4 mil associados no fim de 2024.",
        "O relatório foi publicado na sexta-feira pela diretoria.",
        "Os dados foram consolidados nos balancetes trimestrais.",
        "As tarifas foram revistas nas regiões Norte e Nordeste.",
        "O serviço de consulta funciona sem custo adicional para o cidadão.",
    ],
)
def test_portuguese_contractions_and_sem_are_not_negation(text: str) -> None:
    assert not _has_negation(text)


@pytest.mark.parametrize(
    "text",
    [
        "A diretoria não aprovou o novo regulamento.",
        "O índice jamais foi divulgado pelo órgão.",
        "Nenhum cliente foi afetado pela falha.",
        "A agência nunca publicou a nota técnica.",
        "Nem a diretoria nem o conselho assinaram o termo.",
        "Ninguém contestou o parecer da auditoria.",
    ],
)
def test_portuguese_negators_are_negation(text: str) -> None:
    assert _has_negation(text)


@pytest.mark.parametrize(
    "text",
    ["No changes were made to the policy.", "The board did not approve the merger."],
)
def test_english_negation_is_preserved(text: str) -> None:
    assert _has_negation(text)


def test_contraction_no_does_not_create_false_contradiction() -> None:
    claim = "A cooperativa Serrana tinha 4 mil associados no fim de 2024."
    evidence = "Ao fim de 2024, a cooperativa Serrana tinha 4 mil associados."
    assert _stance(claim, evidence) is Stance.SUPPORTS


def test_real_portuguese_negation_still_refutes() -> None:
    claim = "O conselho da cooperativa Serrana aprovou a fusão."
    evidence = "O conselho da cooperativa Serrana não aprovou a fusão."
    assert _verdict(claim, evidence) is Verdict.REFUTED


# --- 2. Portuguese written and slash dates -----------------------------------------


def test_written_portuguese_dates_are_extracted_with_granularity() -> None:
    assert _extract_dates("Publicado em 10 de março de 2026.") == {("day", 2026, 3, 10)}
    assert _extract_dates("Vigente desde 1º de abril de 2026.") == {("day", 2026, 4, 1)}
    assert _extract_dates("Divulgado em março de 2026.") == {("month", 2026, 3, 0)}


def test_slash_dates_follow_text_language() -> None:
    assert _extract_dates("A portaria foi publicada em 03/04/2026.") == {("day", 2026, 4, 3)}
    assert _extract_dates("The notice was published on 03/04/2026.") == {("day", 2026, 3, 4)}


def test_invalid_calendar_dates_are_ignored() -> None:
    assert _extract_dates("Registrado em 31/02/2026 e em 31 de abril de 2026.") == set()


def test_different_month_same_day_conflicts() -> None:
    claim = "A autarquia publicou o balanço em 10 de março de 2026."
    evidence = "A autarquia publicou o balanço em 10 de abril de 2026."
    assert _dates_conflict(claim, evidence)
    assert _stance(claim, evidence) is Stance.CONTRADICTS


def test_month_granularity_conflict_and_agreement() -> None:
    assert _dates_conflict("Divulgado em março de 2026.", "Divulgado em abril de 2026.")
    assert not _dates_conflict("Divulgado em março de 2026.", "Divulgado em 18 de março de 2026.")


def test_written_and_slash_forms_of_same_date_agree() -> None:
    claim = "A autarquia publicou o balanço em 10 de março de 2026."
    evidence = "A autarquia publicou o balanço em 10/03/2026."
    assert not _dates_conflict(claim, evidence)
    assert _stance(claim, evidence) is Stance.SUPPORTS


def test_written_date_claim_without_evidence_date_is_not_support() -> None:
    claim = "A autarquia publicou o balanço em 10 de março de 2026."
    evidence = "A autarquia publicou o balanço anual."
    assert _stance(claim, evidence) is Stance.NEUTRAL


# --- 3. Directional antonyms -------------------------------------------------------


@pytest.mark.parametrize(
    ("claim", "evidence"),
    [
        (
            "A arrecadação do município Vale Claro subiu 8% em 2025.",
            "A arrecadação do município Vale Claro caiu 8% em 2025.",
        ),
        (
            "O número de usuários do portal Cidadão Digital aumentou 15% em 2025.",
            "O número de usuários do portal Cidadão Digital diminuiu 15% em 2025.",
        ),
        (
            "A assembleia da cooperativa Serrana aprovou o orçamento de 2026.",
            "A assembleia da cooperativa Serrana rejeitou o orçamento de 2026.",
        ),
        (
            "Exports from the Delta port rose 12% in 2025.",
            "Exports from the Delta port fell 12% in 2025.",
        ),
    ],
)
def test_opposite_direction_contradicts(claim: str, evidence: str) -> None:
    assert _stance(claim, evidence) is Stance.CONTRADICTS


def test_same_direction_supports() -> None:
    claim = "A arrecadação do município Vale Claro aumentou 8% em 2025."
    evidence = "Segundo a prefeitura, a arrecadação do município Vale Claro aumentou 8% em 2025."
    assert _stance(claim, evidence) is Stance.SUPPORTS


def test_same_polarity_synonyms_are_not_a_conflict() -> None:
    claim = "A arrecadação do município Vale Claro cresceu em 2025."
    evidence = "A arrecadação do município Vale Claro aumentou em 2025."
    assert _stance(claim, evidence) is not Stance.CONTRADICTS


def test_evidence_with_both_directions_is_not_a_direction_conflict() -> None:
    claim = "A arrecadação do município Vale Claro subiu 8% em 2025."
    evidence = (
        "Em 2025, a arrecadação do município Vale Claro subiu 8% e as despesas "
        "do município Vale Claro caíram."
    )
    assert _stance(claim, evidence) is not Stance.CONTRADICTS


def test_unrelated_text_with_opposite_verb_is_not_a_conflict() -> None:
    claim = "A arrecadação do município Vale Claro subiu 8% em 2025."
    evidence = "O nível do reservatório caiu durante a estiagem."
    assert _stance(claim, evidence) is not Stance.CONTRADICTS
