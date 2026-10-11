from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ayorai_attractor.verification.judge2 import (
    JudgeRulesError,
    RULES_VERSION,
    canonical_json_bytes,
    load_rules,
    rules_sha256,
)


def test_rules_load_with_version_and_stable_content_hash() -> None:
    rules_path = Path(__file__).resolve().parents[2] / "rules" / "judge-2.0.0.json"
    rules, digest = load_rules(rules_path)

    assert rules["judge_rules_version"] == RULES_VERSION == "2.0.0"
    assert rules["authority"] == "deterministic_judge_only"
    assert digest == hashlib.sha256(rules_path.read_bytes()).hexdigest()
    assert rules_sha256(rules_path) == digest


def test_rules_contract_declares_required_gate_atomic_and_composite_rules() -> None:
    rules, _ = load_rules()

    assert {item["code"] for item in rules["input_gate"]} == {
        "SCHEMA_VIOLATION",
        "EMPTY_CLAIM",
        "NO_ATOMS",
        "DUPLICATE_ID",
        "DANGLING_REFERENCE",
        "DUPLICATE_STANCE",
        "ATOM_SPAN_OUT_OF_RANGE",
        "UNSUPPORTED_PROTOCOL_VERSION",
    }
    assert {item["id"] for item in rules["atomic_rules"]} == {"A1", "A2", "A3", "A4"}
    assert {item["id"] for item in rules["composite_rules"]} == {
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
    }


def test_canonical_json_bytes_are_stable_and_utf8() -> None:
    value = {"z": "ação", "a": None}
    expected = b'{"a":null,"z":"a\xc3\xa7\xc3\xa3o"}'

    assert canonical_json_bytes(value) == expected
    assert canonical_json_bytes(value) == canonical_json_bytes(value)


def test_rules_loader_rejects_wrong_version(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "judge-rules/1.0.0",
                "judge_rules_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(JudgeRulesError, match="unsupported Judge rules version"):
        load_rules(path)


def test_rules_loader_rejects_non_object_document(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="must be a JSON object"):
        load_rules(path)
