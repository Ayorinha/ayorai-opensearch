"""Detector v9: token negation is limited to the sentences that state the claim,
and a reported denial ("X negou que P") neither supports nor contradicts P."""

from __future__ import annotations

import pytest

from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _has_negation,
    _reported_denial,
)

CLAIM = "A receita da Vértice foi de 40 milhões em 2024."
CLAIM_TOKENS = frozenset({"receita", "vértice", "foi", "milhões", "2024"})


@pytest.mark.parametrize(
    ("text", "negated"),
    [
        # Single sentence: exactly the token check, as before v9.
        ("A receita da Vértice não foi de 40 milhões em 2024.", True),
        ("A receita da Vértice foi de 40 milhões em 2024.", False),
        # A negator in another proposition does not negate the claim.
        ("A Vértice não faliu. A receita da Vértice foi de 40 milhões em 2024.", False),
        ("A receita da Vértice foi de 40 milhões em 2024. A empresa não comentou.", False),
        # A negator in the sentence that states the claim still counts.
        ("A Vértice cresceu. A receita da Vértice não foi de 40 milhões em 2024.", True),
        # A short sentence with no claim word that denies the previous one counts.
        ("A receita da Vértice foi de 40 milhões em 2024. Isso não é verdade.", True),
        ("A receita da Vértice foi de 40 milhões em 2024. Não procede.", True),
        ("Vértice revenue was 40 million in 2024. That is not true.", True),
        # Decimals and thousands separators are not sentence boundaries.
        ("A receita da Vértice não foi de 40.5 milhões em 2024.", True),
    ],
)
def test_token_negation_is_limited_to_the_claim_sentences(text: str, negated: bool) -> None:
    assert _has_negation(text, CLAIM_TOKENS) is negated


def test_without_claim_tokens_the_whole_text_is_checked_as_before() -> None:
    text = "A Vértice não faliu. A receita da Vértice foi de 40 milhões em 2024."
    assert _has_negation(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "A Vértice negou que a receita da Vértice foi de 40 milhões em 2024.",
        "A diretoria desmentiu que a receita da Vértice foi de 40 milhões em 2024.",
        "Os auditores contestam que a receita da Vértice foi de 40 milhões em 2024.",
        "Vértice denied that the receita da Vértice foi de 40 milhões em 2024.",
    ],
)
def test_a_reported_denial_covering_the_claim_is_detected(text: str) -> None:
    assert _reported_denial(text, CLAIM_TOKENS)


@pytest.mark.parametrize(
    "text",
    [
        "A receita da Vértice foi de 40 milhões em 2024.",
        # The denial is about another proposition.
        "A Vértice negou que vai fechar fábricas. A receita da Vértice foi de 40 milhões em 2024.",
        # "negou" without "que" is not a reported proposition.
        "A Vértice negou o pedido. A receita da Vértice foi de 40 milhões em 2024.",
    ],
)
def test_other_texts_are_not_reported_denials_of_the_claim(text: str) -> None:
    assert not _reported_denial(text, CLAIM_TOKENS)


def test_detector_version_is_9() -> None:
    assert RuleStanceDetector.version == "9"
