from ayorai_attractor.verification.nli import _resolve_label_map


def test_resolve_three_class_label_map() -> None:
    assert _resolve_label_map(
        {0: "entailment", 1: "neutral", 2: "contradiction"}
    ) == {
        0: "supports",
        1: "neutral",
        2: "contradicts",
    }


def test_resolve_label_map_is_case_insensitive() -> None:
    assert _resolve_label_map(
        {0: "CONTRADICTION", 1: "Entailment", 2: "Neutral"}
    )[1] == "supports"


def test_resolve_label_map_rejects_missing_class() -> None:
    try:
        _resolve_label_map({0: "entailment", 1: "neutral"})
    except ValueError as exc:
        assert "exactly entailment, contradiction and neutral" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_resolve_label_map_rejects_unknown_class() -> None:
    try:
        _resolve_label_map({0: "entailment", 1: "neutral", 2: "support"})
    except ValueError as exc:
        assert "exactly entailment, contradiction and neutral" in str(exc)
    else:
        raise AssertionError("expected ValueError")
