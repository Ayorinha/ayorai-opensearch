"""Bounded proposal/evaluation loop primitives for R11.

The optimizer is intentionally model-agnostic: proposal generation may be supplied
by an LLM or another system, while acceptance is determined by explicit metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    payload: str


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    objective: float


class CandidateEvaluator(Protocol):
    def score(self, candidate: Candidate) -> CandidateScore: ...


class BoundedOptimizer:
    """Evaluate a bounded candidate set and return the best score without mutation."""

    def __init__(self, evaluator: CandidateEvaluator, max_candidates: int = 16) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        self._evaluator = evaluator
        self._max_candidates = max_candidates

    def evaluate(self, candidates: list[Candidate]) -> tuple[CandidateScore, ...]:
        if len(candidates) > self._max_candidates:
            raise ValueError("candidate budget exceeded")
        scores = [self._evaluator.score(candidate) for candidate in candidates]
        return tuple(sorted(scores, key=lambda item: (-item.objective, item.candidate_id)))
