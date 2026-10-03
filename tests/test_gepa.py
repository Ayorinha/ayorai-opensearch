import pytest

from ayorai_attractor.gepa import Candidate, optimize


def test_optimize_selects_highest_score_with_stable_tie_break() -> None:
    result = optimize(
        [
            Candidate("z", "prompt-z"),
            Candidate("a", "prompt-a"),
            Candidate("b", "prompt-b"),
        ],
        lambda candidate: 0.8 if candidate.candidate_id != "a" else 0.9,
    )
    assert result.selected.candidate_id == "a"
    assert result.evaluations[0].score == 0.8


def test_tie_break_is_lexicographically_deterministic() -> None:
    result = optimize(
        [Candidate("z", "z"), Candidate("a", "a")],
        lambda _: 1.0,
    )
    assert result.selected.candidate_id == "a"


def test_duplicate_candidate_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="candidate_id"):
        optimize(
            [Candidate("same", "a"), Candidate("same", "b")],
            lambda _: 1.0,
        )
