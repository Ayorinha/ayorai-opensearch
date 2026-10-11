"""Contract-driven deterministic atomic and composite adjudication for Judge 2.0.0.

Only gate-admitted, validated evidence can contribute. Clusters and provenance
are derived from the validated Evidence objects carried by GateResult.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from ayorai_attractor.verification.clusters import cluster_evidence
from ayorai_attractor.verification.models import Evidence

from . import load_rules
from .gates import GateResult

Stance = Literal["SUPPORTS", "CONTRADICTS"]
_ROBUSTNESS_RANK = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


@dataclass(frozen=True)
class DecisionEvidence:
    """Caller-declared stance edge, checked against the stance validated by gates."""

    evidence_id: str
    atom_id: str
    stance: Stance


@dataclass(frozen=True)
class AtomicDecision:
    atom_id: str
    verdict: str
    robustness: str
    robustness_support: str
    robustness_contradiction: str
    support_clusters: int
    contradiction_clusters: int
    rule_id: str


@dataclass(frozen=True)
class CompositeDecision:
    verdict: str
    robustness: str
    rule_id: str
    atom_count: int


def _rule_id(rule_id: str) -> str:
    return f"2.0.0/{rule_id}"


def _atomic_verdict(
    rules: dict[str, Any], supports: int, contradicts: int
) -> tuple[str, str]:
    for rule in rules["atomic_rules"]:
        conditions = rule["when"]
        matches = True
        for key, expected in conditions.items():
            actual = supports if key == "support_clusters" else contradicts
            if expected == 0:
                matches = matches and actual == 0
            elif expected == ">=1":
                matches = matches and actual >= 1
            else:
                raise ValueError(f"unsupported atomic predicate: {key}={expected!r}")
        if matches:
            return rule["verdict"], rule["id"]
    raise ValueError("atomic rules do not cover this cluster-count combination")


def _robustness(
    rules: dict[str, Any], items: list[Evidence]
) -> tuple[str, str, int]:
    clusters = cluster_evidence(items)
    if not clusters:
        predicate = "no_admissible_decision_cluster"
    elif len(clusters) == 1:
        predicate = "exactly_one_decision_cluster_on_evaluated_side"
    elif any(not item.provenance_complete for item in items):
        predicate = "at_least_two_clusters_and_any_relevant_provenance_incomplete"
    else:
        predicate = "at_least_two_clusters_and_all_relevant_provenance_complete"
    rule = next(item for item in rules["robustness_rules"] if item["when"] == predicate)
    return rule["value"], rule["id"], len(clusters)


def adjudicate_atoms(
    atom_ids: list[str],
    evidence: list[DecisionEvidence],
    gates: GateResult,
) -> list[AtomicDecision]:
    """Adjudicate using gate-validated stance and provenance, never caller metadata."""
    rules, _ = load_rules()
    if gates.decision_state is not None or not gates.admissible:
        raise ValueError("cannot adjudicate when pre-adjudication gates did not pass")
    if not atom_ids or len(atom_ids) != len(set(atom_ids)):
        raise ValueError("atom_ids must be non-empty and unique")

    declared: dict[tuple[str, str], DecisionEvidence] = {}
    for item in evidence:
        if item.atom_id not in atom_ids:
            raise ValueError(f"unknown atom id: {item.atom_id}")
        key = (item.evidence_id, item.atom_id)
        if key in declared:
            raise ValueError("duplicate evidence/atom decision edge")
        if item.stance not in ("SUPPORTS", "CONTRADICTS"):
            raise ValueError("only explicit SUPPORTS or CONTRADICTS edges are decisive")
        declared[key] = item

    dispositions: dict[tuple[str, str], Any] = {}
    for disposition in gates.evidence:
        key = (disposition.evidence_id, disposition.atom_id)
        if key in dispositions:
            raise ValueError("duplicate evidence/atom gate disposition")
        dispositions[key] = disposition

    for key, item in declared.items():
        matched_disposition = dispositions.get(key)
        if matched_disposition is None:
            raise ValueError("decision evidence has no matching GateResult disposition")
        if (
            matched_disposition.stance is not None
            and item.stance != matched_disposition.stance
        ):
            raise ValueError("caller stance differs from stance validated by GateResult")

    by_atom_side: dict[str, dict[str, list[Evidence]]] = defaultdict(
        lambda: {"SUPPORTS": [], "CONTRADICTS": []}
    )
    for key, disposition in dispositions.items():
        if not disposition.admitted:
            continue
        if key not in declared:
            raise ValueError("admitted GateResult edge is missing from decision evidence")
        if disposition.stance not in ("SUPPORTS", "CONTRADICTS"):
            raise ValueError("admitted GateResult edge has no validated decisive stance")
        if disposition.source_evidence is None:
            raise ValueError("admitted GateResult edge has no validated source evidence")
        by_atom_side[disposition.atom_id][disposition.stance].append(
            disposition.source_evidence
        )

    results: list[AtomicDecision] = []
    for atom_id in atom_ids:
        sides = by_atom_side[atom_id]
        support_robustness, _, supports = _robustness(rules, sides["SUPPORTS"])
        contradiction_robustness, _, contradicts = _robustness(rules, sides["CONTRADICTS"])
        verdict, rule_id = _atomic_verdict(rules, supports, contradicts)
        if verdict == "SUPPORTED":
            robustness = support_robustness
        elif verdict == "REFUTED":
            robustness = contradiction_robustness
        elif verdict == "CONFLICTING":
            robustness = min(
                (support_robustness, contradiction_robustness),
                key=lambda value: _ROBUSTNESS_RANK[value],
            )
        else:
            robustness = "R0"
        results.append(
            AtomicDecision(
                atom_id=atom_id,
                verdict=verdict,
                robustness=robustness,
                robustness_support=support_robustness,
                robustness_contradiction=contradiction_robustness,
                support_clusters=supports,
                contradiction_clusters=contradicts,
                rule_id=_rule_id(rule_id),
            )
        )
    return results


def adjudicate_composite(atom_decisions: list[AtomicDecision]) -> CompositeDecision:
    """Apply K1–K5 in normative precedence order and derive selected-side robustness."""
    rules, _ = load_rules()
    allowed_verdicts = set(rules["enums"]["verdict"])
    allowed_robustness = set(rules["enums"]["robustness"])
    if not atom_decisions:
        raise ValueError("atom_decisions must be non-empty")
    for decision in atom_decisions:
        if decision.verdict not in allowed_verdicts:
            raise ValueError("atom decision contains an invalid Judge 2 verdict")
        if decision.robustness not in allowed_robustness:
            raise ValueError("atom decision contains an invalid robustness enum")

    by_id = {rule["id"]: rule for rule in rules["composite_rules"]}
    for rule_id in rules["composite_precedence"]:
        rule = by_id[rule_id]
        predicate = rule["when"]
        verdicts = [item.verdict for item in atom_decisions]
        if predicate == "any_atom_REFUTED":
            matched = "REFUTED" in verdicts
        elif predicate == "otherwise_any_atom_CONFLICTING":
            matched = "CONFLICTING" in verdicts
        elif predicate == "all_atoms_SUPPORTED":
            matched = all(value == "SUPPORTED" for value in verdicts)
        elif predicate == "otherwise_any_atom_SUPPORTED":
            matched = "SUPPORTED" in verdicts
        elif predicate == "otherwise":
            matched = True
        else:
            raise ValueError(f"unsupported composite predicate: {predicate}")
        if not matched:
            continue

        selector = rule.get("robustness_atoms")
        if selector is None:
            robustness = rule.get("robustness", "R0")
        else:
            selected = [
                item.robustness for item in atom_decisions if item.verdict == selector
            ]
            robustness = min(selected, key=lambda value: _ROBUSTNESS_RANK[value])
        if robustness not in allowed_robustness:
            raise ValueError("composite rule produced an invalid robustness enum")
        return CompositeDecision(
            verdict=rule["verdict"],
            robustness=robustness,
            rule_id=_rule_id(rule["id"]),
            atom_count=len(atom_decisions),
        )
    raise ValueError("composite rules did not produce a decision")
