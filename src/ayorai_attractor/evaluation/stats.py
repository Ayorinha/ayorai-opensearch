"""Statistical evaluation utilities for deterministic benchmark reports.

The functions here deliberately operate on already-computed labels. They never
choose a verdict and never call an LLM.
"""

from __future__ import annotations

from collections import Counter
from math import comb
from random import Random
from collections.abc import Sequence

from ayorai_attractor.verification.models import Verdict

VERDICT_ORDER: tuple[str, ...] = tuple(item.value.upper() for item in Verdict)


def confusion_matrix(
    expected: Sequence[str],
    predicted: Sequence[str],
) -> dict[str, dict[str, int]]:
    """Return a deterministic 6x6-style matrix over the Judge verdict states."""
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")
    allowed = set(VERDICT_ORDER)
    if any(label not in allowed for label in expected) or any(
        label not in allowed for label in predicted
    ):
        raise ValueError("labels must be Judge verdict states")
    counts: Counter[tuple[str, str]] = Counter(zip(expected, predicted, strict=True))
    return {
        gold: {guess: counts[(gold, guess)] for guess in VERDICT_ORDER}
        for gold in VERDICT_ORDER
    }


def bootstrap_accuracy(
    expected: Sequence[str],
    predicted: Sequence[str],
    *,
    iterations: int = 10_000,
    seed: int = 20261003,
) -> tuple[float, float]:
    """Return a deterministic percentile bootstrap 95% CI for accuracy."""
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have the same length")
    if not expected:
        raise ValueError("at least one observation is required")
    if iterations < 1:
        raise ValueError("iterations must be positive")
    outcomes = [gold == guess for gold, guess in zip(expected, predicted, strict=True)]
    rng = Random(seed)
    samples: list[float] = []
    size = len(outcomes)
    for _ in range(iterations):
        correct = sum(outcomes[rng.randrange(size)] for _ in range(size))
        samples.append(correct / size)
    samples.sort()
    low = samples[int(0.025 * (iterations - 1))]
    high = samples[int(0.975 * (iterations - 1))]
    return low, high


def mcnemar_exact_pvalue(
    expected: Sequence[str],
    predicted_a: Sequence[str],
    predicted_b: Sequence[str],
) -> float:
    """Return the two-sided exact McNemar p-value for paired predictions."""
    if not (len(expected) == len(predicted_a) == len(predicted_b)):
        raise ValueError("all sequences must have the same length")
    b = sum(
        a == gold and c != gold
        for gold, a, c in zip(expected, predicted_a, predicted_b, strict=True)
    )
    c = sum(
        a != gold and d == gold
        for gold, a, d in zip(expected, predicted_a, predicted_b, strict=True)
    )
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(comb(discordant, k) for k in range(0, min(b, c) + 1)) / (2**discordant)
    return min(1.0, 2 * tail)
