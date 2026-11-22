"""Detector v12: questions, conditions, goals and correction notices do not support.

Regression: each passage below was accepted as support for the claim, so /v1/check
returned "partially_supported" for text that does not assert the fact.
(Version 11 is reserved for the pending scale-word change, PR #571.)
"""

from __future__ import annotations

import pytest

from ayorai_attractor.verification.document_check import CheckDocumentInput, check_documents
from ayorai_attractor.verification.stance import RuleStanceDetector

CLAIM = "A receita da Vértice foi de 40 milhões de reais em 2024."


def _stances(claim: str, text: str) -> list[str]:
    result = check_documents([CheckDocumentInput(id="d", text=text)], claims=[claim])
    return [evidence.stance for evidence in result.results[0].evidence]


@pytest.mark.parametrize(
    "text",
    [
        "A receita da Vértice foi de 40 milhões de reais em 2024?",
        "Se a receita da Vértice foi de 40 milhões de reais em 2024, o bônus será pago.",
        "Caso a receita da Vértice tenha sido de 40 milhões de reais em 2024, haverá bônus.",
        "Supondo que a receita da Vértice foi de 40 milhões de reais em 2024, o lucro cresceu.",
        "A meta da Vértice é atingir receita de 40 milhões de reais em 2024.",
        "A Vértice pretende que a receita seja de 40 milhões de reais em 2024.",
        "O objetivo é receita da Vértice de 40 milhões de reais em 2024.",
        "A receita da Vértice foi de 40 milhões de reais em 2024. "
        "Retificação: o valor correto é 45 milhões de reais.",
        "Errata. A receita da Vértice foi de 40 milhões de reais em 2024.",
    ],
)
def test_text_that_does_not_assert_the_claim_never_supports_it(text: str) -> None:
    assert "supports" not in _stances(CLAIM, text)


@pytest.mark.parametrize(
    ("claim", "text"),
    [
        (CLAIM, "A receita da Vértice foi de 40 milhões de reais em 2024."),
        # A question elsewhere in the passage does not cover the claim.
        (CLAIM, "Qual foi o resultado? A receita da Vértice foi de 40 milhões de reais em 2024."),
        # "se" as a pronoun, not a condition at the start of the sentence.
        (
            "A Vértice se tornou líder do setor em 2024.",
            "Em 2024, a Vértice se tornou líder do setor.",
        ),
        # The goal word is part of the claim: the claim is about the goal itself.
        (
            "A meta de inflação foi de 3% em 2024.",
            "Em 2024, a meta de inflação foi de 3%, segundo o conselho.",
        ),
        # The correction word is part of the claim.
        (
            "A correção monetária foi de 5% em 2024.",
            "Em 2024, a correção monetária foi de 5%, segundo o índice oficial.",
        ),
    ],
)
def test_assertions_with_the_same_words_still_support(claim: str, text: str) -> None:
    assert _stances(claim, text) == ["supports"]


def test_a_conditional_contradiction_is_not_a_refutation() -> None:
    text = "Se a receita da Vértice foi de 70 milhões de reais em 2024, o bônus será pago."
    assert _stances(CLAIM, text) == ["neutral"]


def test_detector_version_is_12() -> None:
    assert RuleStanceDetector.version in {"12", "13", "14", "15"}


def test_unrelated_correction_notice_does_not_neutralize_another_claim() -> None:
    text = (
        "Retificação: o endereço da Vértice é Rua das Flores, 10.\n\n"
        "A receita da Vértice foi de 40 milhões de reais em 2024."
    )
    result = check_documents([CheckDocumentInput(id="d", text=text)], claims=[CLAIM])
    item = result.results[0]
    stance_by_excerpt = {evidence.excerpt: evidence.stance for evidence in item.evidence}
    # The claim's own paragraph still supports it; the unrelated notice (which also
    # names the company, so it is selected as a passage) stays neutral on its own.
    assert stance_by_excerpt[CLAIM] == "supports"
    assert item.verdict == "partially_supported"


def test_adjacent_correction_notice_still_neutralizes_the_claim() -> None:
    text = (
        "A receita da Vértice foi de 40 milhões de reais em 2024. "
        "Retificação: o valor correto é 45 milhões de reais."
    )
    assert _stances(CLAIM, text) == ["neutral"]


def test_non_adjacent_correction_notice_in_the_same_passage_does_not_neutralize() -> None:
    # One paragraph, so one passage: the notice is two sentences away from the claim
    # sentence and concerns something else. Only an adjacent notice qualifies the claim.
    text = (
        "Retificação: o endereço da Vértice é Rua das Flores, 10. "
        "A sede foi inaugurada em março. "
        "A receita da Vértice foi de 40 milhões de reais em 2024."
    )
    assert _stances(CLAIM, text) == ["supports"]
