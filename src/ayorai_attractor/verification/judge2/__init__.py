"""Versioned deterministic Judge 2.0.0 rule-contract loader.

This module validates the normative rule data and computes its canonical identity.
It does not yet replace the legacy r1-a judge or adjudicate claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .gates import EvidenceDisposition, GateResult, evaluate_gates

RULES_VERSION = "2.0.0"
_RULES_PATH = Path(__file__).resolve().parents[4] / "rules" / "judge-2.0.0.json"

_ROOT_FIELDS = {
    "schema_version",
    "judge_rules_version",
    "normative_source",
    "authority",
    "invariants",
    "enums",
    "input_gate",
    "abstention",
    "evidence_admissibility",
    "atomic_rules",
    "robustness_rules",
    "composite_rules",
    "composite_precedence",
    "output",
    "compatibility",
    "protocol_tests",
}
_ATOMIC_WHEN_FIELDS = {"support_clusters", "contradiction_clusters"}
_ATOMIC_WHEN_VALUES = {0, ">=1"}
_ROBUSTNESS_PREDICATES = {
    "no_admissible_decision_cluster",
    "exactly_one_decision_cluster_on_evaluated_side",
    "at_least_two_clusters_and_any_relevant_provenance_incomplete",
    "at_least_two_clusters_and_all_relevant_provenance_complete",
}
_COMPOSITE_PREDICATES = {
    "any_atom_REFUTED",
    "otherwise_any_atom_CONFLICTING",
    "all_atoms_SUPPORTED",
    "otherwise_any_atom_SUPPORTED",
    "otherwise",
}
_RULE_FIELDS = {
    "input_gate": {"id", "rule_id", "code", "outcome"},
    "abstention": {"id", "rule_id", "code", "outcome"},
    "evidence_admissibility": {"id", "criterion", "rejection", "source_unavailable_rejection"},
    "atomic_rules": {"id", "when", "verdict"},
    "robustness_rules": {"id", "when", "value", "label"},
    "composite_rules": {"id", "when", "verdict", "robustness_atoms", "robustness"},
}
_EXPECTED_CODES = {
    "input_gate": {
        "SCHEMA_VIOLATION",
        "EMPTY_CLAIM",
        "NO_ATOMS",
        "DUPLICATE_ID",
        "DANGLING_REFERENCE",
        "DUPLICATE_STANCE",
        "ATOM_SPAN_OUT_OF_RANGE",
        "UNSUPPORTED_PROTOCOL_VERSION",
    },
    "abstention": {
        "OUT_OF_SCOPE",
        "NON_FACTUAL_CLAIM",
        "MISSING_TEMPORAL_ANCHOR",
        "RETRIEVAL_FAILURE",
        "EVIDENCE_POOL_INTEGRITY_FAILURE",
    },
}
_EXPECTED_IDS = {
    "atomic_rules": {"A1", "A2", "A3", "A4"},
    "robustness_rules": {"R0", "R1", "R2", "R3"},
    "composite_rules": {"K1", "K2", "K3", "K4", "K5"},
    "evidence_admissibility": {"E1", "E2", "E3"},
}


class JudgeRulesError(ValueError):
    """Raised when the versioned Judge rules are missing or malformed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON using the ADR-009 canonical encoding."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _validate_rules(rules: dict[str, Any]) -> None:
    unknown_root = set(rules) - _ROOT_FIELDS
    missing_root = _ROOT_FIELDS - set(rules)
    if unknown_root or missing_root:
        raise JudgeRulesError(
            f"invalid Judge rules fields: unknown={sorted(unknown_root)}, "
            f"missing={sorted(missing_root)}"
        )

    enums = rules["enums"]
    for enum_name in ("decision_state", "verdict", "robustness"):
        if not isinstance(enums.get(enum_name), list) or not enums[enum_name]:
            raise JudgeRulesError(f"enums.{enum_name} must be a non-empty list")
        if len(enums[enum_name]) != len(set(enums[enum_name])):
            raise JudgeRulesError(f"enums.{enum_name} contains duplicate values")

    all_rule_ids: list[str] = []
    for section, allowed_fields in _RULE_FIELDS.items():
        entries = rules.get(section)
        if not isinstance(entries, list):
            raise JudgeRulesError(f"{section} must be a list")
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise JudgeRulesError(f"{section}[{index}] must be an object")
            unknown = set(entry) - allowed_fields
            required_fields = allowed_fields
            if section in {"input_gate", "abstention"}:
                required_fields = allowed_fields
            elif section == "composite_rules":
                required_fields = {"id", "when", "verdict"}
                if not ({"robustness_atoms", "robustness"} & set(entry)):
                    raise JudgeRulesError(
                        f"composite_rules[{index}] needs a robustness field"
                    )
            missing = required_fields - set(entry)
            if unknown or missing:
                raise JudgeRulesError(
                    f"invalid fields in {section}[{index}]: "
                    f"unknown={sorted(unknown)}, missing={sorted(missing)}"
                )
            if "id" in entry:
                if section in {"input_gate", "abstention"}:
                    all_rule_ids.append(entry["rule_id"])
                else:
                    all_rule_ids.append(entry["id"])

            if "verdict" in entry and entry["verdict"] not in enums["verdict"]:
                raise JudgeRulesError(
                    f"invalid verdict in {section}[{index}]: {entry['verdict']!r}"
                )
            if "outcome" in entry and entry["outcome"] not in enums["decision_state"]:
                raise JudgeRulesError(
                    f"invalid outcome in {section}[{index}]: {entry['outcome']!r}"
                )
            if "robustness" in entry and entry["robustness"] not in enums["robustness"]:
                raise JudgeRulesError(
                    f"invalid robustness in {section}[{index}]: {entry['robustness']!r}"
                )
            if section == "robustness_rules" and entry.get("value") not in enums["robustness"]:
                raise JudgeRulesError(
                    f"invalid robustness value in {section}[{index}]: {entry.get('value')!r}"
                )

    if len(all_rule_ids) != len(set(all_rule_ids)):
        raise JudgeRulesError("duplicate rule_id or rule id detected")

    for section, expected_codes in _EXPECTED_CODES.items():
        entries = rules[section]
        codes = [entry.get("code") for entry in entries]
        if len(codes) != len(set(codes)) or set(codes) != expected_codes:
            raise JudgeRulesError(
                f"{section} must contain each expected G code exactly once"
            )
        expected_id = "G1" if section == "input_gate" else "G2"
        expected_outcome = "INVALID_INPUT" if expected_id == "G1" else "ABSTAINED"
        for entry in entries:
            if entry.get("id") != expected_id:
                raise JudgeRulesError(f"{section} entries must all use id {expected_id}")
            if entry.get("outcome") != expected_outcome:
                raise JudgeRulesError(
                    f"{section} entries must all use outcome {expected_outcome}"
                )
            expected_rule_id = f"2.0.0/{expected_id}:{entry['code']}"
            if entry.get("rule_id") != expected_rule_id:
                raise JudgeRulesError(
                    f"invalid rule_id for {entry['code']}: expected {expected_rule_id}"
                )

    e1 = next(item for item in rules["evidence_admissibility"] if item["id"] == "E1")
    if e1.get("source_unavailable_rejection") != "SOURCE_UNAVAILABLE":
        raise JudgeRulesError("E1 source_unavailable_rejection must be SOURCE_UNAVAILABLE")

    for section, expected_ids in _EXPECTED_IDS.items():
        entries = rules[section]
        ids = [entry.get("id") for entry in entries]
        if len(ids) != len(set(ids)) or set(ids) != expected_ids:
            raise JudgeRulesError(
                f"{section} must contain each expected rule ID exactly once"
            )

    for index, rule in enumerate(rules["atomic_rules"]):
        predicate = rule["when"]
        if not isinstance(predicate, dict) or not predicate:
            raise JudgeRulesError(f"atomic_rules[{index}].when must be an object")
        unknown = set(predicate) - _ATOMIC_WHEN_FIELDS
        if unknown:
            raise JudgeRulesError(
                f"unknown atomic predicate fields: {sorted(unknown)}"
            )
        if any(value not in _ATOMIC_WHEN_VALUES for value in predicate.values()):
            raise JudgeRulesError(
                f"unknown atomic predicate value in rule {rule['id']}"
            )

    for section, predicates in (
        ("robustness_rules", _ROBUSTNESS_PREDICATES),
        ("composite_rules", _COMPOSITE_PREDICATES),
    ):
        for rule in rules[section]:
            if rule["when"] not in predicates:
                raise JudgeRulesError(
                    f"unknown predicate in {section}: {rule['when']!r}"
                )

    expected_precedence = ["K1", "K2", "K3", "K4", "K5"]
    if rules["composite_precedence"] != expected_precedence:
        raise JudgeRulesError(
            "composite_precedence must explicitly order K1 through K5"
        )
    if [rule["id"] for rule in rules["composite_rules"]] != rules["composite_precedence"]:
        raise JudgeRulesError("composite rules must follow composite_precedence")


def load_rules(path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    """Load validated Judge rules and return the document plus canonical SHA-256."""
    rules_path = Path(path) if path is not None else _RULES_PATH
    try:
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JudgeRulesError(f"cannot load Judge rules from {rules_path}") from exc
    if not isinstance(rules, dict):
        raise JudgeRulesError("Judge rules document must be a JSON object")
    if rules.get("judge_rules_version") != RULES_VERSION:
        raise JudgeRulesError("unsupported Judge rules version")
    if rules.get("schema_version") != "judge-rules/2.0.0":
        raise JudgeRulesError("unsupported Judge rules schema")
    _validate_rules(rules)
    return rules, hashlib.sha256(canonical_json_bytes(rules)).hexdigest()


def rules_sha256(path: str | Path | None = None) -> str:
    """Return the canonical content SHA-256 for the selected Judge rules."""
    return load_rules(path)[1]


RULES_SHA256 = rules_sha256()


__all__ = [
    "EvidenceDisposition",
    "GateResult",
    "RULES_SHA256",
    "evaluate_gates",
    "JudgeRulesError",
    "RULES_VERSION",
    "canonical_json_bytes",
    "load_rules",
    "rules_sha256",
]
