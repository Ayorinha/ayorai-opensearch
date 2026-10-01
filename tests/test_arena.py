from ayorai_attractor.arena import ArenaCase, score_system


def test_arena_score_is_reproducible() -> None:
    cases = [ArenaCase("a", "verified"), ArenaCase("b", "refuted")]
    score = score_system("system-a", cases, {"a": "verified", "b": "unverified"})
    assert score.correct == 1
    assert score.total == 2
    assert score.accuracy == 0.5
