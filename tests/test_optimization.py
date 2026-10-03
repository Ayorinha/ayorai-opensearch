from dataclasses import dataclass

import pytest

from ayorai_attractor.optimization import (
    BoundedOptimizer,
    Candidate,
    CandidateScore,
)


@dataclass
class FixedEvaluator:
    scores: dict[str, float]

    def score(self, candidate: Candidate) -> CandidateScore:
        return CandidateScore(candidate.candidate_id, self.scores[candidate.candidate_id])


def test_optimizer_is_bounded_and_deterministic() -> None:
    evaluator = FixedEvaluator({"b": 0.8, "a": 0.8, "c": 0.2})
    result = BoundedOptimizer(evaluator, max_candidates=3).evaluate(
        [Candidate("c", "c"), Candidate("b", "b"), Candidate("a", "a")]
    )
    assert result == (
        CandidateScore("a", 0.8),
        CandidateScore("b", 0.8),
        CandidateScore("c", 0.2),
    )


def test_optimizer_rejects_budget_overflow() -> None:
    evaluator = FixedEvaluator({"a": 1.0, "b": 0.0})
    with pytest.raises(ValueError, match="budget"):
        BoundedOptimizer(evaluator, max_candidates=1).evaluate(
            [Candidate("a", "a"), Candidate("b", "b")]
        )


def test_optimizer_rejects_invalid_budget() -> None:
    with pytest.raises(ValueError, match="positive"):
        BoundedOptimizer(FixedEvaluator({}), max_candidates=0)
