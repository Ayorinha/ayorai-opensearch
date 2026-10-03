from ayorai_attractor.evaluation.arena import EvaluationArena


def test_arena_is_reproducible_and_does_not_rank_systems() -> None:
    expected = ("VERIFIED", "SUPPORTED", "REFUTED", "UNVERIFIED")
    predictions = {
        "system-b": ("VERIFIED", "SUPPORTED", "REFUTED", "UNVERIFIED"),
        "system-a": ("VERIFIED", "REFUTED", "REFUTED", "UNVERIFIED"),
    }
    arena = EvaluationArena()
    results = arena.evaluate(expected, predictions, bootstrap_iterations=500, seed=7)
    assert [item.system_id for item in results] == ["system-a", "system-b"]
    assert results[1].accuracy == 1.0
    assert arena.evaluate(expected, predictions, bootstrap_iterations=500, seed=7) == results


def test_paired_comparison_is_deterministic() -> None:
    expected = ("VERIFIED", "SUPPORTED", "REFUTED")
    predictions = {
        "a": ("VERIFIED", "SUPPORTED", "REFUTED"),
        "b": ("SUPPORTED", "SUPPORTED", "REFUTED"),
    }
    results = EvaluationArena().evaluate(expected, predictions, bootstrap_iterations=100, seed=3)
    comparisons = EvaluationArena().paired(expected, results)
    assert len(comparisons) == 1
    assert comparisons[0].system_a == "a"
    assert comparisons[0].system_b == "b"
    assert comparisons[0].mcnemar_exact_pvalue == 1.0


def test_arena_rejects_missing_predictions() -> None:
    try:
        EvaluationArena().evaluate(
            ("VERIFIED", "SUPPORTED"),
            {"system-a": ("VERIFIED",)},
        )
    except ValueError as exc:
        assert "different number" in str(exc)
    else:
        raise AssertionError("mismatched prediction lengths must fail")
