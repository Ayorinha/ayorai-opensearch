from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ayorai_attractor.verification.judge2 import (
    RULES_VERSION,
    JudgeRulesError,
    canonical_json_bytes,
    load_rules,
    rules_sha256,
)


def test_rules_load_with_version_and_canonical_content_hash() -> None:
    rules_path = Path(__file__).resolve().parents[2] / "rules" / "judge-2.0.0.json"
    rules, digest = load_rules(rules_path)

    assert rules["judge_rules_version"] == RULES_VERSION == "2.0.0"
    assert rules["authority"] == "deterministic_judge_only"
    assert digest == hashlib.sha256(canonical_json_bytes(rules)).hexdigest()
    assert rules_sha256(rules_path) == digest


def test_contract_has_adr_aligned_rule_ids_and_explicit_precedence() -> None:
    rules, _ = load_rules()
    duplicate_id = next(item for item in rules["input_gate"] if item["code"] == "DUPLICATE_ID")
    out_of_scope = next(item for item in rules["abstention"] if item["code"] == "OUT_OF_SCOPE")

    assert duplicate_id["id"] == "G1"
    assert out_of_scope["id"] == "G2"
    assert rules["composite_precedence"] == ["K1", "K2", "K3", "K4", "K5"]
    assert [item["id"] for item in rules["composite_rules"]] == rules["composite_precedence"]
    assert {item["id"] for item in rules["atomic_rules"]} == {"A1", "A2", "A3", "A4"}


def test_reformatting_json_does_not_change_canonical_hash(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "rules" / "judge-2.0.0.json"
    original = json.loads(source.read_text(encoding="utf-8"))
    compact_reordered = json.dumps(
        original, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path = tmp_path / "rules.json"
    path.write_text(compact_reordered, encoding="utf-8")

    assert rules_sha256(path) == hashlib.sha256(canonical_json_bytes(original)).hexdigest()


def test_changing_a_rule_changes_canonical_hash(tmp_path: Path) -> None:
    rules, original_digest = load_rules()
    rules["atomic_rules"][0]["verdict"] = "SUPPORTED"
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=7), encoding="utf-8")

    assert rules_sha256(path) != original_digest


def test_canonical_json_bytes_are_stable_and_utf8() -> None:
    value = {"z": "ação", "a": None}
    expected = '{"a":null,"z":"ação"}'.encode()

    assert canonical_json_bytes(value) == expected
    assert canonical_json_bytes(value) == canonical_json_bytes(value)


def test_rules_loader_rejects_wrong_version(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    rules, _ = load_rules()
    rules["schema_version"] = "judge-rules/1.0.0"
    rules["judge_rules_version"] = "1.0.0"
    path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="unsupported Judge rules version"):
        load_rules(path)


def test_rules_loader_rejects_non_object_document(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="must be a JSON object"):
        load_rules(path)


def test_rules_loader_rejects_unknown_predicate(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["atomic_rules"][0]["when"]["invented_field"] = 0
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="unknown atomic predicate fields"):
        load_rules(path)


def test_rules_loader_rejects_unknown_rule_field(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["composite_rules"][0]["surprise"] = True
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="invalid fields in composite_rules"):
        load_rules(path)


def test_rules_loader_rejects_reordered_composite_precedence(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["composite_precedence"] = ["K2", "K1", "K3", "K4", "K5"]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(JudgeRulesError, match="composite_precedence"):
        load_rules(path)
