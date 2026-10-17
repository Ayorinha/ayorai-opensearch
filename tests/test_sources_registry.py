from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evals" / "ptbr" / "SOURCES-REGISTRY.json"
SCHEMA_PATH = ROOT / "evals" / "ptbr" / "SOURCES-REGISTRY.schema.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load(SCHEMA_PATH), format_checker=FormatChecker())


def _verified_source() -> dict[str, Any]:
    source = copy.deepcopy(_load(REGISTRY_PATH)["sources"][0])
    source.update(
        {
            "status": "verified",
            "sha256": "a" * 64,
            "retrieved_at": "2026-10-11T12:00:00Z",
            "capture_method": "HTTP GET; bytes preserved without normalization",
            "artifact_path": "artifacts/sources/example.html",
            "content_type": "text/html",
        }
    )
    return source


def test_real_source_registry_validates_with_format_checker() -> None:
    validator = _validator()
    errors = list(validator.iter_errors(_load(REGISTRY_PATH)))
    assert errors == []


def test_verified_source_requires_sha256() -> None:
    source = _verified_source()
    source.pop("sha256")
    errors = list(_validator().iter_errors({"schema_version": "1.0.0", "sources": [source]}))
    assert errors


def test_verified_source_requires_retrieved_at() -> None:
    source = _verified_source()
    source.pop("retrieved_at")
    errors = list(_validator().iter_errors({"schema_version": "1.0.0", "sources": [source]}))
    assert errors


def test_sha256_with_63_characters_is_rejected() -> None:
    registry = _load(REGISTRY_PATH)
    registry["sources"][0]["sha256"] = "a" * 63
    errors = list(_validator().iter_errors(registry))
    assert errors


def test_unknown_source_field_is_rejected() -> None:
    registry = _load(REGISTRY_PATH)
    registry["sources"][0]["unreviewed_field"] = "not allowed"
    errors = list(_validator().iter_errors(registry))
    assert errors


def test_format_checker_has_required_optional_validators() -> None:
    checker = FormatChecker()
    assert "date-time" in checker.checkers
    assert "uri" in checker.checkers


def test_invalid_retrieved_at_format_is_rejected() -> None:
    registry = _load(REGISTRY_PATH)
    source = _verified_source()
    source["retrieved_at"] = "ontem"
    registry["sources"][0] = source
    errors = list(_validator().iter_errors(registry))
    assert any("retrieved_at" in str(error.path) for error in errors)


def test_invalid_publication_date_is_rejected() -> None:
    registry = _load(REGISTRY_PATH)
    source = _verified_source()
    source["publication_date"] = "2023-13-40"
    registry["sources"][0] = source
    errors = list(_validator().iter_errors(registry))
    assert any("publication_date" in str(error.path) for error in errors)


def test_invalid_source_url_format_is_rejected() -> None:
    registry = _load(REGISTRY_PATH)
    source = _verified_source()
    source["url"] = "nao eh url"
    registry["sources"][0] = source
    errors = list(_validator().iter_errors(registry))
    assert any("url" in str(error.path) for error in errors)
