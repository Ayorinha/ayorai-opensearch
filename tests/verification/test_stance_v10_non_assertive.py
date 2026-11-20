"""Detector v10: non-assertive framing and bounded values do not confirm a claim."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _has_bound,
    _non_assertive,
)

CLAIM = "A receita da Vértice foi de 40 milhões em 2024."
CLAIM_TOKENS = frozenset({"receita", "vértice", "foi", "milhões", "2024"})


@pytest.mark.parametrize(
    "text",
    [
        "A receita da Vértice pode ter sido de 40 milhões em 2024.",
        "Estima-se que a receita da Vértice foi de 40 milhões em 2024.",
        "Rumores indicam que a receita da Vértice foi de 40 milhões em 2024.",
        "A receita da Vértice deve atingir 40 milhões em 2024, segundo projeções.",
        "Se a receita da Vértice fosse de 40 milhões em 2024, haveria lucro.",
        "Não se sabe se a receita da Vértice foi de 40 milhões em 2024.",
        "Ninguém sabe se a receita da Vértice foi de 40 milhões em 2024.",
        "A receita da Vértice provavelmente foi de 40 milhões em 2024.",
        "Vértice receita reportedly foi de 40 milhões em 2024.",
    ],
)
def test_non_assertive_framing_of_the_claim_is_detected(text: str) -> None:
    assert _non_assertive(text, CLAIM_TOKENS)


@pytest.mark.parametrize(
    "text",
    [
        "A receita da Vértice foi de 40 milhões em 2024.",
        # Hedge in another sentence, about another proposition.
        "A Vértice pode ter perdido clientes. A receita da Vértice foi de 40 milhões em 2024.",
        # Affirmative legal and technical wording is not a hedge.
        "A receita da Vértice foi de 40 milhões em 2024, conforme previsto no balanço.",
        "A receita da Vértice deverá ser declarada; foi de 40 milhões em 2024.",
        "A concessão não pode ter duração superior a 30 anos.",
        # "não pode ter sido" denies (it is handled as negation), it does not hedge.
        "A receita da Vértice não pode ter sido de 40 milhões em 2024.",
    ],
)
def test_affirmative_wording_is_not_non_assertive(text: str) -> None:
    assert not _non_assertive(text, CLAIM_TOKENS)


@pytest.mark.parametrize(
    ("text", "bounded"),
    [
        ("A receita superou 40 milhões.", True),
        ("A receita ficou abaixo de 40 milhões.", True),
        ("Mais de 800 funcionários.", True),
        ("At least 800 employees.", True),
        ("A receita foi de 40 milhões em 2024.", False),
        ("Até 2024 a receita foi de 40 milhões.", False),  # a year is never a bound
    ],
)
def test_bounds_are_recognised(text: str, bounded: bool) -> None:
    assert _has_bound(text) is bounded


def _first_stance(claim: str, document: str) -> str:
    response = TestClient(app).post(
        "/v1/check", json={"claims": [claim], "documents": [{"id": "d", "text": document}]}
    )
    assert response.status_code == 200
    stance = response.json()["results"][0]["evidence"][0]["stance"]
    assert isinstance(stance, str)
    return stance


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("A receita da Vértice pode ter sido de 40 milhões em 2024.", "neutral"),
        ("Não se sabe se a receita da Vértice foi de 40 milhões em 2024.", "neutral"),
        ("A receita da Vértice superou 40 milhões em 2024.", "neutral"),
        ("A receita da Vértice ficou abaixo de 40 milhões em 2024.", "neutral"),
        # Controls: plain statements keep their stance.
        ("A receita da Vértice foi de 40 milhões em 2024.", "supports"),
        ("A receita da Vértice foi de 45 milhões em 2024.", "contradicts"),
        ("A receita da Vértice não chegou a 40 milhões em 2024.", "contradicts"),
        # A year after "até" is a time anchor, not a bounded value.
        ("Até 2024, a receita da Vértice foi de 40 milhões.", "supports"),
    ],
)
def test_check_end_to_end(document: str, expected: str) -> None:
    assert _first_stance(CLAIM, document) == expected


def test_bound_claims_still_compare_with_bound_evidence() -> None:
    assert (
        _first_stance(
            "A AtlasGrid tinha mais de 800 funcionários em 2025.",
            "A AtlasGrid tinha mais de 800 funcionários em 2025.",
        )
        == "supports"
    )


def test_detector_version_is_10() -> None:
    assert RuleStanceDetector.version == "10"
