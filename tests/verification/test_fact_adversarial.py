"""Adversarial regression suite for the deterministic FACT numeric layer.

These cases are derived from the specification (ADR-002/ADR-006), not from
Golden v0: an unverifiable number must never yield SUPPORTS, magnitudes are
compared after locale and scale normalization, and calendar years are exact.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    SentenceNLIStanceDetector,
    _numeric_facts_align,
)

S, C, N = Stance.SUPPORTS, Stance.CONTRADICTS, Stance.NEUTRAL

CASES = [
    ("Revenue was 100 million USD.", "The figure is 120 million USD.", N),
    ("Company X revenue was 100 million USD.", "Company Y revenue was 100 million USD.", N),
    ("Revenue was 100 million USD.", "Revenue was 120 million USD.", C),
    ("Revenue was 100 million USD.", "Revenue was 100 million USD.", S),
    (
        "A receita da Empresa X foi de 100 milhões de USD.",
        "Company X revenue was 120 million USD.",
        C,
    ),
    (
        "A receita da Empresa X foi de 120 milhões de USD.",
        "Company X revenue was 120 million USD.",
        S,
    ),
    ("A receita foi de 1,5 milhão de USD.", "Revenue was 1.5 million USD.", S),
    ("A receita foi de R$ 1.200 milhões.", "A receita foi de R$ 1,2 bilhão.", S),
    ("Revenue was USD 1.2 billion.", "Revenue was USD 1,200 million.", S),
    ("Revenue was USD 1.2 billion.", "Revenue was USD 1.2 million.", C),
    ("Revenue was 100 million USD.", "Revenue was 100 million EUR.", N),
    ("Revenue was 100 million USD.", "Profit was 100 million USD.", N),
    ("Revenue was 100 million USD.", "Revenue was 100.5 million USD.", S),
    ("Revenue was 100 million USD.", "Revenue was 102 million USD.", C),
    (
        "AtlasGrid revenue was USD 120 million in 2025.",
        "AtlasGrid revenue was USD 120 million in fiscal year 2024.",
        C,
    ),
    ("AtlasGrid had 800 employees.", "AtlasGrid had 900 employees.", C),
    ("AtlasGrid had 800 employees.", "AtlasGrid had 800 customers.", N),
    ("A AtlasGrid tem 800 funcionários.", "AtlasGrid had 800 employees.", S),
    ("Margin was 12%.", "Margin was 15%.", C),
    ("A margem foi de 12 por cento.", "Margin was 12%.", S),
    ("Revenue was not 100 million USD.", "Revenue was 100 million USD.", C),
    ("Latency is 50 ms.", "Latency is 50 milliseconds.", S),
    ("Receita: US$ 10 milhões", "Revenue: $10 million", S),
    ("A VectorLabs bloqueia artefatos não assinados.", "VectorLabs blocks unsigned artifacts.", N),
    ("The patch AG-001 shipped on 2026-03-10.", "The patch AG-001 shipped on 2026-03-10.", S),
]


def _claim(text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id="c1", text=text),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fake", "1", "in", "out"),
    )


def _evidence(text: str) -> Evidence:
    return Evidence(
        id="e1",
        claim_id="c1",
        source_id="source-a",
        source_location="body",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
        start_offset=0,
        end_offset=len(text),
        excerpt=text,
        origin_id="origin-a",
    )


@pytest.mark.parametrize(("claim", "excerpt", "expected"), CASES)
def test_fact_layer_adversarial(claim: str, excerpt: str, expected: Stance) -> None:
    result = RuleStanceDetector().detect([_claim(claim)], [_evidence(excerpt)])
    assert result.edges[0].edge.stance is expected


def test_fact_layer_never_raises_on_free_text() -> None:
    vocab = (
        "R$ US$ $ € USD EUR BRL 2025 1.200 1,5 1.2.3 ,,, 0 -5 +3 99% % million "
        "milhões bilhão de of in em fiscal year ano receita revenue margin Company "
        "Empresa X not não ms employees por cento 2026-01-01 AG-001 10,000.50"
    ).split()
    rng = random.Random(20261003)
    for _ in range(3000):
        left = " ".join(rng.choice(vocab) for _ in range(rng.randint(0, 14)))
        right = " ".join(rng.choice(vocab) for _ in range(rng.randint(0, 14)))
        _numeric_facts_align(left, right)


def test_provenance_input_hash_separates_claim_and_excerpt() -> None:
    """Claim and excerpt are hashed with a newline separator (ADR-002 provenance).

    Without a separator, ("ab", "c") and ("a", "bc") would share one hash.
    """
    import hashlib

    first = RuleStanceDetector().detect([_claim("ab")], [_evidence("c")])
    second = RuleStanceDetector().detect([_claim("a")], [_evidence("bc")])
    expected = hashlib.sha256(b"ab\nc").hexdigest()
    assert first.edges[0].provenance.input_sha256 == expected
    assert first.edges[0].provenance.input_sha256 != second.edges[0].provenance.input_sha256


class _FakeNLI:
    def classify(self, claim: str, evidence: str) -> dict[str, object]:
        if "contradiction" in evidence:
            return {"stance": "contradicts", "confidence": 0.9}
        return {"stance": "supports", "confidence": 0.8}


def test_sentence_h1_splits_and_preserves_offsets() -> None:
    evidence = _evidence("First sentence. Second sentence!")
    detector = SentenceNLIStanceDetector(
        _FakeNLI(), model="fake", version="1", tie_precedence="contradicts"
    )
    spans = detector._windows(evidence)
    assert [item[2] for item in spans] == ["First sentence.", "Second sentence!"]
    assert spans[0][:2] == (0, 15)
    assert spans[1][:2] == (16, 33)


def test_sentence_h1_tie_prefers_contradicts() -> None:
    class TieNLI:
        def classify(self, claim: str, evidence: str) -> dict[str, object]:
            return {"stance": "contradicts" if "second" in evidence else "supports", "confidence": 0.8}

    detector = SentenceNLIStanceDetector(
        TieNLI(), model="fake", version="1", tie_precedence="contradicts"
    )
    result = detector.detect([_claim("claim")], [_evidence("first. second.")])
    assert result.edges[0].edge.stance is Stance.CONTRADICTS
