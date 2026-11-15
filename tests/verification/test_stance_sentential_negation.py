"""Sentential negation operators in the rule stance detector (v7).

"É falso que X" declares X false without any negator token. Each operator flips
polarity once, a negator directly before it cancels it, and text without an
operator keeps the v6 token-based classification exactly. An operator reaches
only the end of its clause and, when the claim is known, counts only if that
clause holds at least half of the claim's content tokens.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _has_negation,
    _has_token_negation,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("text", "negated"),
    [
        ("É falso que a receita foi de 40 milhões.", True),
        ("é FALSO QUE a receita foi de 40 milhões.", True),
        ("É incorreto afirmar que o prazo é de 10 dias.", True),
        ("É inverídico dizer que o prazo é de 10 dias.", True),
        ("É mentira que o prazo é de 10 dias.", True),
        ("It is false that revenue was 40 million.", True),
        ("It is untrue to say that revenue was 40 million.", True),
        # Double negation: the proposition is affirmed.
        ("Não é falso que a receita foi de 40 milhões.", False),
        ("Nunca é falso que a receita foi de 40 milhões.", False),
        ("É falso que a receita não foi de 40 milhões.", False),
        ("It is not false that revenue was 40 million.", False),
        # Triple negation.
        ("Não é falso que a receita não foi de 40 milhões.", True),
        # Not operators: no proposition introduced, or a reported denial.
        ("A notícia é falsa.", False),
        ("A empresa negou que a receita foi de 40 milhões.", False),
        ("O boato de que a receita foi de 40 milhões é falso.", False),
        # Token negation is unchanged.
        ("Não é verdade que a receita foi de 40 milhões.", True),
        ("A receita não foi de 40 milhões.", True),
        ("No fim de 2025 a receita foi de 40 milhões.", False),
        ("Revenue was not 40 million.", True),
    ],
)
def test_sentential_negation(text: str, negated: bool) -> None:
    assert _has_negation(text) is negated


def _evaluation_texts() -> list[str]:
    texts: list[str] = []
    with (ROOT / "evals/pt-cp-audit/cases.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            texts += [case["claim"], case["evidence"]]
    with (ROOT / "evals/corpus/documents.jsonl").open(encoding="utf-8") as handle:
        texts += [json.loads(line)["content"] for line in handle]
    return texts


def test_text_without_an_operator_keeps_the_token_classification() -> None:
    texts = _evaluation_texts()
    assert len(texts) > 300
    for text in texts:
        assert _has_negation(text) is _has_token_negation(text), text


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
    ("evidence", "stance"),
    [
        ("É falso que a receita da Vértice foi de 40 milhões em 2024.", Stance.CONTRADICTS),
        ("Não é falso que a receita da Vértice foi de 40 milhões em 2024.", Stance.SUPPORTS),
        ("A receita da Vértice foi de 40 milhões em 2024.", Stance.SUPPORTS),
    ],
)
def test_detector_uses_sentential_negation(evidence: str, stance: Stance) -> None:
    assert _stance("A receita da Vértice foi de 40 milhões em 2024.", evidence) == stance


CLAIM_TOKENS = frozenset({"receita", "vértice", "foi", "milhões", "2024"})


@pytest.mark.parametrize(
    ("text", "negated"),
    [
        ("É falso que a receita da Vértice foi de 40 milhões em 2024.", True),
        # The operator's clause is about something else: it does not count.
        ("É falso que a Vértice faliu. A receita da Vértice foi de 40 milhões em 2024.", False),
        ("É falso que a Vértice faliu, e a receita da Vértice foi de 40 milhões em 2024.", False),
        ("É falso que a Vértice faliu; a receita da Vértice foi de 40 milhões em 2024.", False),
        # A later clause with an operator that covers the claim still counts.
        ("A Vértice cresceu. É falso que a receita da Vértice foi de 40 milhões em 2024.", True),
        # Without a counted operator the text is classified as in v6 (the "não"
        # of an uncounted operator still counts there, a known v6 limitation).
        ("Não é falso que a Vértice faliu. A receita da Vértice foi de 40 milhões em 2024.", True),
        # With a counted operator, an uncounted operator's "não" is not a negator.
        (
            "Não é falso que a Vértice faliu. "
            "É falso que a receita da Vértice foi de 40 milhões em 2024.",
            True,
        ),
    ],
)
def test_operator_counts_only_when_its_clause_covers_the_claim(text: str, negated: bool) -> None:
    assert _has_negation(text, CLAIM_TOKENS) is negated


def test_operator_scope_is_ignored_without_claim_tokens() -> None:
    text = "É falso que a Vértice faliu. A receita da Vértice foi de 40 milhões em 2024."
    assert _has_negation(text) is True
    assert _has_negation(text, frozenset()) is True


def test_an_operator_about_another_sentence_does_not_contradict() -> None:
    evidence = "É falso que a Vértice faliu. A receita da Vértice foi de 40 milhões em 2024."
    claim = "A receita da Vértice foi de 40 milhões em 2024."
    assert _stance(claim, evidence) == Stance.SUPPORTS


def test_detector_version_is_7() -> None:
    assert RuleStanceDetector.version in {"7", "8"}
