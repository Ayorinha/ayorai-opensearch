"""The rules shipped inside the package must be byte-identical to rules/."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ayorai_attractor.verification import judge2

REPO_RULES = Path(__file__).resolve().parents[2] / "rules" / "judge-2.0.0.json"
CANONICAL_RULES_SHA256 = "493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc"


def test_packaged_rules_are_byte_identical_to_repository_rules() -> None:
    packaged = judge2._PACKAGED_RULES_PATH.read_bytes()
    repository = REPO_RULES.read_bytes()
    assert hashlib.sha256(packaged).hexdigest() == hashlib.sha256(repository).hexdigest()


def test_packaged_rules_load_with_the_canonical_rules_sha256() -> None:
    _, digest = judge2.load_rules(judge2._PACKAGED_RULES_PATH)
    assert digest == CANONICAL_RULES_SHA256


def test_source_checkout_uses_repository_rules() -> None:
    assert judge2._RULES_PATH == REPO_RULES.resolve()
    _, digest = judge2.load_rules()
    assert digest == CANONICAL_RULES_SHA256


def test_installed_layout_falls_back_to_packaged_rules(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Simulate an installed package: no src/ directory above the package.
    monkeypatch.setattr(judge2, "_SOURCE_ROOT", Path("/nonexistent/site-packages"))
    assert judge2._default_rules_path() == judge2._PACKAGED_RULES_PATH
