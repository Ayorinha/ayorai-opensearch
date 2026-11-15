"""Comparison baselines in evidence (rule detector v8).

"caiu para 31, contra 40 no ano anterior": the 40 describes another period. A
number introduced as the baseline of a comparison is removed from the evidence
facts, so it neither confirms nor contradicts the claim. Text without such a
marker is unchanged; bounds ("more than 40"), prepositions ("contra 3
operadoras") and calendar years are not baselines.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import RuleStanceDetector, _mask_comparison_baselines

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        (
            "caiu para 31 em 2024, contra 40 no ano anterior.",
            "caiu para 31 em 2024, contra   no ano anterior.",
        ),
        ("O índice ficou em 31, ante 40 em 2023.", "O índice ficou em 31, ante   em 2023."),
        ("A receita caiu de 40 para 31 milhões.", "A receita caiu de   para 31 milhões."),
        ("Revenue was 31, versus 40 a year earlier.", "Revenue was 31, versus   a year earlier."),
        ("Revenue fell from 40 to 31.", "Revenue fell from   to 31."),
        ("Foram 31 em 2024 contra 40 em 2023.", "Foram 31 em 2024 contra   em 2023."),
        ("Foram 31 milhões contra 40 milhões.", "Foram 31 milhões contra   milhões."),
        ("Subiu 5% contra 3% em 2023.", "Subiu 5% contra  % em 2023."),
        ("Comparado com 40 em 2023, foram 31.", "Comparado com   em 2023, foram 31."),
        ("Foram 31, contra R$ 40 em 2023.", "Foram 31, contra R$   em 2023."),
    ],
)
def test_baseline_numbers_are_removed(text: str, masked: str) -> None:
    assert _mask_comparison_baselines(text) == masked


@pytest.mark.parametrize(
    "text",
    [
        "A receita foi de 40 milhões em 2024.",
        "A multa de R$ 40 mil foi aplicada contra a empresa.",
        "Prazo de 10 dias para resposta e de 30 para recurso.",
        "O recurso foi interposto contra a decisão de 2023.",
        # "than" marks a bound, not a baseline.
        "Revenue was higher than 40.",
        "AtlasGrid had more than 800 employees.",
        # "contra" as a preposition, not a comparison.
        "A Vértice venceu ações contra 3 operadoras em 2024.",
        # Calendar years are time anchors.
        "Revenue has grown from 2023 to 2025.",
        "O prazo passou de 2023 para 2024.",
    ],
)
def test_text_without_a_baseline_is_unchanged(text: str) -> None:
    assert _mask_comparison_baselines(text) == text


def test_evaluation_texts_contain_no_baseline() -> None:
    texts: list[str] = []
    with (ROOT / "evals/pt-cp-audit/cases.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            texts += [case["claim"], case["evidence"]]
    with (ROOT / "evals/corpus/documents.jsonl").open(encoding="utf-8") as handle:
        texts += [json.loads(line)["content"] for line in handle]
    assert len(texts) > 300
    for text in texts:
        assert _mask_comparison_baselines(text) == text, text


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
        retrieved_at=datetime(2026, 11, 15, tzinfo=UTC),
        start_offset=0,
        end_offset=len(evidence),
        excerpt=evidence,
        origin_id="o1",
    )
    return RuleStanceDetector().detect([extracted], [item]).edges[0].edge.stance


@pytest.mark.parametrize(
    ("claim", "evidence", "stance"),
    [
        # The baseline value no longer confirms the claim.
        (
            "O número de reclamações foi 40 em 2024.",
            "O número de reclamações caiu para 31 em 2024, contra 40 no ano anterior.",
            Stance.NEUTRAL,
        ),
        (
            "A receita da Vértice foi de 40 milhões em 2024.",
            "A receita da Vértice caiu de 40 para 31 milhões em 2024.",
            Stance.CONTRADICTS,
        ),
        (
            "A receita da Vértice foi de 40 milhões em 2024.",
            "A receita da Vértice foi de 31 milhões em 2024, versus 40 milhões em 2023.",
            Stance.CONTRADICTS,
        ),
        # Regressions found in review: bounds, prepositions and year ranges.
        (
            "AtlasGrid had more than 800 employees in 2025.",
            "AtlasGrid had more than 800 employees in 2025.",
            Stance.SUPPORTS,
        ),
        (
            "A Vértice venceu ações contra 3 operadoras em 2024.",
            "A Vértice venceu ações contra 3 operadoras em 2024.",
            Stance.SUPPORTS,
        ),
        # The current value still supports.
        (
            "O número de reclamações foi 31 em 2024.",
            "O número de reclamações caiu para 31 em 2024, contra 40 no ano anterior.",
            Stance.SUPPORTS,
        ),
        (
            "A receita da Vértice foi de 31 milhões em 2024.",
            "A receita da Vértice caiu de 40 para 31 milhões em 2024.",
            Stance.SUPPORTS,
        ),
    ],
)
def test_detector_ignores_baseline_numbers(claim: str, evidence: str, stance: Stance) -> None:
    assert _stance(claim, evidence) == stance


def test_a_year_range_does_not_refute_a_claim_about_its_start() -> None:
    stance = _stance("Revenue has grown since 2023.", "Revenue has grown from 2023 to 2025.")
    assert stance != Stance.CONTRADICTS


def test_detector_version_is_8() -> None:
    assert RuleStanceDetector.version == "8"
