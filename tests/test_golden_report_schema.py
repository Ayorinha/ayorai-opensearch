from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError

from ayorai_attractor.evaluation.golden import evaluate_golden_v0


def test_golden_report_conforms_to_versioned_json_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "docs" / "schemas" / "golden-evaluation-report-v1.schema.json"
    schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    report = evaluate_golden_v0(
        root / "evals" / "golden" / "v0.jsonl",
        root / "evals" / "corpus" / "documents.jsonl",
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)


def test_golden_report_schema_rejects_each_missing_digest_field() -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "docs" / "schemas" / "golden-evaluation-report-v1.schema.json"
    schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    report = evaluate_golden_v0(
        root / "evals" / "golden" / "v0.jsonl",
        root / "evals" / "corpus" / "documents.jsonl",
    )

    # Validate each required digest/provenance field independently. Starting
    # from a valid report prevents unrelated required fields from satisfying
    # this negative test.
    for field in ("content_sha256", "semantic_digest_version", "semantic_sha256"):
        incomplete = dict(report)
        incomplete.pop(field)
        with pytest.raises(ValidationError, match="required"):
            validator.validate(incomplete)
