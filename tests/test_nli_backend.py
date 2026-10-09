from ayorai_attractor.verification.nli import (
    EVAL_ONLY_LEVEL,
    EVAL_ONLY_MODEL,
    EVAL_ONLY_REVISION,
    TransformersNLIBackend,
    _license_guard,
    _resolve_label_map,
)


def test_nli_backend_requires_explicit_license_level() -> None:
    import pytest

    with pytest.raises(TypeError, match="license_level"):
        TransformersNLIBackend("fixture-model", "immutable-revision")


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


def test_eval_only_model_requires_evaluation_or_opt_in() -> None:
    try:
        _license_guard(EVAL_ONLY_LEVEL, evaluation_mode=False, license_opt_in=False)
    except PermissionError as exc:
        assert "EVAL_ONLY model rejected" in str(exc)
    else:
        raise AssertionError("expected PermissionError")


def test_eval_only_gate_allows_evaluation_mode() -> None:
    assert _license_guard(EVAL_ONLY_LEVEL, evaluation_mode=True, license_opt_in=False) == (
        "evaluation_mode=true"
    )


def test_eval_only_gate_records_explicit_opt_in() -> None:
    backend = TransformersNLIBackend(
        EVAL_ONLY_MODEL,
        EVAL_ONLY_REVISION,
        license_level=EVAL_ONLY_LEVEL,
        license_opt_in=True,
    )
    assert backend.provenance_version.endswith("license_opt_in=true")
