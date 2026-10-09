from __future__ import annotations

import pytest

from ayorai_attractor.verification.translation import MarianTranslationBackend


def test_translation_provenance_defaults_to_registry_license_level() -> None:
    backend = MarianTranslationBackend("fixture-model", "immutable-revision")

    assert backend.provenance_version == (
        "fixture-model@immutable-revision|license=COMMERCIAL_DEFAULT"
    )


def test_translation_provenance_accepts_explicit_eval_only_level() -> None:
    backend = MarianTranslationBackend(
        "fixture-model",
        "immutable-revision",
        license_level="EVAL_ONLY",
    )

    assert backend.provenance_version == (
        "fixture-model@immutable-revision|license=EVAL_ONLY"
    )


def test_translation_backend_rejects_unknown_license_level() -> None:
    with pytest.raises(ValueError, match="license_level must be one of"):
        MarianTranslationBackend(
            "fixture-model",
            "immutable-revision",
            license_level="UNKNOWN",
        )
