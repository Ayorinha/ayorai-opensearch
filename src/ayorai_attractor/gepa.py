"""Deterministic optimization primitives for R11.

The core is evaluator-driven: candidates are data, evaluation is explicit, and
selection is reproducible. No hidden model or stochastic mutation is performed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    value: str


@dataclass(frozen=True)
class Evaluation:
    candidate_id: str
    score: float


@dataclass(frozen=True)
class OptimizationResult:
    selected: Candidate
    evaluations: tuple[Evaluation, ...]


Evaluator = Callable[[Candidate], float]


def optimize(
    candidates: Sequence[Candidate],
    evaluator: Evaluator,
) -> OptimizationResult:
    """Evaluate all candidates and select the highest score deterministically."""
    if not candidates:
        raise ValueError("at least one candidate is required")
    ids = [candidate.candidate_id for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique")

    evaluations = tuple(
        Evaluation(candidate.candidate_id, float(evaluator(candidate)))
        for candidate in candidates
    )
    selected_id = min(
        evaluations,
        key=lambda item: (-item.score, item.candidate_id),
    ).candidate_id
    selected = next(
        candidate for candidate in candidates if candidate.candidate_id == selected_id
    )
    return OptimizationResult(selected=selected, evaluations=evaluations)
