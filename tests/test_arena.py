import pytest

from ayorai_attractor.arena import ArenaCase, compare_systems, score_system


def test_arena_score_is_reproducible() -> None:
    cases = [ArenaCase("a", "verified"), ArenaCase("b", "refuted")]
    score = score_system("system-a", cases, {"a": "verified", "b": "unverified"})
    assert score.correct == 1
    assert score.total == 2
    assert score.accuracy == 0.5


def test_arena_comparison_reports_statistics_without_ranking() -> None:
    cases = [
        ArenaCase("a", "VERIFIED"),
        ArenaCase("b", "SUPPORTED"),
        ArenaCase("c", "REFUTED"),
        ArenaCase("d", "UNVERIFIED"),
    ]
    report = compare_systems(
        cases,
        {
            "baseline": {"a": "VERIFIED", "b": "SUPPORTED", "c": "REFUTED", "d": "UNVERIFIED"},
            "candidate": {"a": "VERIFIED", "b": "REFUTED", "c": "REFUTED", "d": "UNVERIFIED"},
        },
        bootstrap_iterations=1000,
        bootstrap_seed=7,
    )
    assert report.bootstrap_intervals["baseline"] == (1.0, 1.0)
    assert report.scores[1].accuracy == 0.75
    assert report.pairwise_mcnemar[("baseline", "candidate")] < 1.0
    assert report.confusion_matrices["candidate"]["SUPPORTED"]["REFUTED"] == 1


def test_arena_rejects_missing_prediction() -> None:
    with pytest.raises(ValueError, match="missing prediction"):
        compare_systems(
            [ArenaCase("a", "VERIFIED")],
            {"system-a": {}},
            bootstrap_iterations=10,
        )
