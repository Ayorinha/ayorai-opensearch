from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from rfc8785 import IntegerDomainError

from ayorai_attractor.verification.judge2 import (
    RULES_VERSION,
    JudgeRulesError,
    canonical_json_bytes,
    load_rules,
    rules_sha256,
)


def _rules_path() -> Path:
    return Path(__file__).resolve().parents[2] / "rules" / "judge-2.0.0.json"


def _write_rules(path: Path, rules: dict[str, object]) -> None:
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def test_rules_load_with_version_and_canonical_content_hash() -> None:
    rules, digest = load_rules(_rules_path())

    assert rules["judge_rules_version"] == RULES_VERSION == "2.0.0"
    assert rules["authority"] == "deterministic_judge_only"
    assert digest == hashlib.sha256(canonical_json_bytes(rules)).hexdigest()
    assert digest == "493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc"
    assert rules_sha256(_rules_path()) == digest


def test_contract_has_all_rule_ids_and_explicit_precedence() -> None:
    rules, _ = load_rules()
    assert {item["id"] for item in rules["input_gate"]} == {"G1"}
    assert {item["id"] for item in rules["abstention"]} == {"G2"}
    assert {item["rule_id"] for item in rules["input_gate"]} == {
        f"2.0.0/G1:{item['code']}" for item in rules["input_gate"]
    }
    assert {item["rule_id"] for item in rules["abstention"]} == {
        f"2.0.0/G2:{item['code']}" for item in rules["abstention"]
    }
    assert {item["id"] for item in rules["atomic_rules"]} == {"A1", "A2", "A3", "A4"}
    assert {item["id"] for item in rules["robustness_rules"]} == {"R0", "R1", "R2", "R3"}
    assert {item["id"] for item in rules["composite_rules"]} == {"K1", "K2", "K3", "K4", "K5"}
    assert {item["id"] for item in rules["evidence_admissibility"]} == {"E1", "E2", "E3"}
    assert rules["composite_precedence"] == ["K1", "K2", "K3", "K4", "K5"]
    assert [item["id"] for item in rules["composite_rules"]] == rules["composite_precedence"]


def test_reformatting_json_does_not_change_canonical_hash(tmp_path: Path) -> None:
    original, _ = load_rules()
    compact_reordered = json.dumps(
        original, ensure_ascii=False, sort_keys=False, separators=(",", ":")
    )
    path = tmp_path / "rules.json"
    path.write_text(compact_reordered, encoding="utf-8")

    assert rules_sha256(path) == hashlib.sha256(canonical_json_bytes(original)).hexdigest()


def test_changing_a_rule_changes_canonical_hash(tmp_path: Path) -> None:
    rules, original_digest = load_rules()
    rules["atomic_rules"][0]["verdict"] = "SUPPORTED"
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    assert rules_sha256(path) != original_digest


def test_canonical_json_bytes_are_stable_and_utf8() -> None:
    value = {"z": "ação", "a": None}
    expected = '{"a":null,"z":"ação"}'.encode()

    assert canonical_json_bytes(value) == expected
    assert canonical_json_bytes(value) == canonical_json_bytes(value)


def test_rules_loader_rejects_wrong_version(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["schema_version"] = "judge-rules/1.0.0"
    rules["judge_rules_version"] = "1.0.0"
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

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
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="unknown atomic predicate fields"):
        load_rules(path)


def test_rules_loader_rejects_unknown_rule_field(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["composite_rules"][0]["surprise"] = True
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="invalid fields in composite_rules"):
        load_rules(path)


def test_rules_loader_rejects_reordered_composite_precedence(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["composite_precedence"] = ["K2", "K1", "K3", "K4", "K5"]
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="composite_precedence"):
        load_rules(path)


def test_rules_loader_rejects_missing_atomic_rule_a4(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["atomic_rules"] = [item for item in rules["atomic_rules"] if item["id"] != "A4"]
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="atomic_rules must contain each expected rule ID"):
        load_rules(path)


def test_rules_loader_rejects_unknown_composite_verdict(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["composite_rules"][0]["verdict"] = "VERIFIED"
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="invalid verdict"):
        load_rules(path)


def test_rules_loader_rejects_missing_g_rule_id(tmp_path: Path) -> None:
    rules, _ = load_rules()
    del rules["input_gate"][0]["id"]
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="missing=.*id"):
        load_rules(path)


def test_rules_loader_rejects_duplicate_rule_id(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["abstention"][1]["rule_id"] = rules["abstention"][0]["rule_id"]
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="duplicate rule_id"):
        load_rules(path)


def test_rules_loader_rejects_invalid_decision_state(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["input_gate"][0]["outcome"] = "REJECTED"
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="invalid outcome"):
        load_rules(path)


def test_rules_loader_rejects_invalid_robustness_enum(tmp_path: Path) -> None:
    rules, _ = load_rules()
    rules["robustness_rules"][0]["value"] = "R9"
    path = tmp_path / "rules.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match="invalid robustness value"):
        load_rules(path)


@pytest.mark.parametrize(
    ("section", "expected_outcome"),
    [("input_gate", "INVALID_INPUT"), ("abstention", "ABSTAINED")],
)
def test_rules_loader_rejects_non_normative_g_outcome(
    tmp_path: Path, section: str, expected_outcome: str
) -> None:
    rules, _ = load_rules()
    rules[section][0]["outcome"] = "DECIDED"
    path = tmp_path / f"{section}.json"
    _write_rules(path, rules)

    with pytest.raises(JudgeRulesError, match=f"must all use outcome {expected_outcome}"):
        load_rules(path)



def test_canonical_json_bytes_follow_rfc8785_number_and_utf16_key_order() -> None:
    value = {"value": 1.0}
    assert canonical_json_bytes(value) == b'{"value":1}'

    # RFC 8785 sorts names by UTF-16 code units; the emoji surrogate pair sorts
    # before U+E000 even though Python code-point ordering places U+E000 first.
    ordered = {"\ue000": "private-use", "😀": "emoji", "á": "accent"}
    assert canonical_json_bytes(ordered) == (
        '{"á":"accent","😀":"emoji","\ue000":"private-use"}'.encode("utf-8")
    )


def test_canonical_json_bytes_rfc8785_integer_accent_and_null_vectors() -> None:
    assert canonical_json_bytes({"z": "ação", "a": None, "n": 7}) == (
        '{"a":null,"n":7,"z":"ação"}'.encode()
    )

def test_rfc8785_accepts_only_safe_integer_boundary() -> None:
    maximum = 2**53 - 1
    assert canonical_json_bytes({"n": maximum}) == (
        f'{{"n":{maximum}}}'.encode("ascii")
    )
    assert canonical_json_bytes({"n": -maximum}) == (
        f'{{"n":{-maximum}}}'.encode("ascii")
    )
    for unsafe in (2**53, 2**53 + 1, 2**60, -(2**53), -(2**53 + 1), -(2**60)):
        with pytest.raises(IntegerDomainError):
            canonical_json_bytes({"n": unsafe})

