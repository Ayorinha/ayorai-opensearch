from __future__ import annotations

import pytest

from ayorai_attractor.verification.translation import MarianTranslationBackend


def test_translation_backend_requires_explicit_license_level() -> None:
    with pytest.raises(TypeError, match="license_level"):
        MarianTranslationBackend("fixture-model", "immutable-revision")


def test_translation_commercial_default_records_guard_state() -> None:
    backend = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="COMMERCIAL_DEFAULT",
    )

    assert backend.provenance_version.endswith("license_opt_in=false")


def test_translation_eval_only_is_rejected_without_evaluation_or_opt_in() -> None:
    backend = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
    )

    with pytest.raises(PermissionError, match="EVAL_ONLY model rejected"):
        backend.translate("this must fail before model loading")


def test_translation_eval_only_in_evaluation_mode_records_gate_state() -> None:
    backend = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
        evaluation_mode=True,
    )

    assert backend.provenance_version == (
        "fixture-model@immutable-revision|license=EVAL_ONLY|evaluation_mode=true"
    )


def test_translation_eval_only_allows_explicit_opt_in_and_records_it() -> None:
    backend = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
        license_opt_in=True,
    )

    assert backend.provenance_version.endswith("license_opt_in=true")


def test_translation_backend_rejects_unknown_license_level() -> None:
    with pytest.raises(ValueError, match="license_level must be one of"):
        MarianTranslationBackend(
            "fixture-model",
            "immutable-revision",
            license_level="UNKNOWN",
        )
