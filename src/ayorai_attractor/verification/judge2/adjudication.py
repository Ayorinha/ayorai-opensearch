"""Contract-driven deterministic atomic and composite adjudication for Judge 2.0.0.

Only evidence explicitly admitted by the item-2.2 GateResult can contribute.
This module does not call probabilistic components.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from . import load_rules
from .gates import GateResult

Stance = Literal["SUPPORTS", "CONTRADICTS"]


@dataclass(frozen=True)
class DecisionEvidence:
    """Decision-side evidence metadata; admission is taken only from GateResult."""

    evidence_id: str
    atom_id: str
    stance: Stance
    cluster_id: str
    provenance_complete: bool


@dataclass(frozen=True)
class AtomicDecision:
    atom_id: str
    verdict: str
    robustness: str
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


def _atomic_verdict(rules: dict[str, Any], supports: int, contradicts: int) -> tuple[str, str]:
    for rule in rules["atomic_rules"]:
        conditions = rule["when"]
        if all(
            (supports == 0 if value == 0 else supports >= 1)
            if key == "support_clusters"
            else (contradicts == 0 if value == 0 else contradicts >= 1)
            for key, value in conditions.items()
        ):
            return rule["verdict"], rule["id"]
    raise ValueError("atomic rules do not cover this cluster-count combination")


def _robustness(rules: dict[str, Any], clusters: list[DecisionEvidence]) -> tuple[str, str]:
    if not clusters:
        predicate = "no_admissible_decision_cluster"
    elif len({item.cluster_id for item in clusters}) == 1:
        predicate = "exactly_one_decision_cluster_on_evaluated_side"
    elif any(not item.provenance_complete for item in clusters):
        predicate = "at_least_two_clusters_and_any_relevant_provenance_incomplete"
    else:
        predicate = "at_least_two_clusters_and_all_relevant_provenance_complete"
    rule = next(item for item in rules["robustness_rules"] if item["when"] == predicate)
    return rule["value"], rule["id"]


def adjudicate_atoms(
    atom_ids: list[str],
    evidence: list[DecisionEvidence],
    gates: GateResult,
) -> list[AtomicDecision]:
    """Adjudicate atoms from admitted evidence only; reject malformed references."""
    rules, _ = load_rules()
    if gates.decision_state is not None or not gates.admissible:
        raise ValueError("cannot adjudicate when pre-adjudication gates did not pass")
    if not atom_ids or len(atom_ids) != len(set(atom_ids)):
        raise ValueError("atom_ids must be non-empty and unique")
    admitted = {
        (item.evidence_id, item.atom_id)
        for item in gates.evidence
        if item.admitted
    }
    seen: set[tuple[str, str]] = set()
    by_atom: dict[str, list[DecisionEvidence]] = defaultdict(list)
    for item in evidence:
        if item.atom_id not in atom_ids:
            raise ValueError(f"unknown atom id: {item.atom_id}")
        key = (item.evidence_id, item.atom_id)
        if key in seen:
            raise ValueError("duplicate evidence/atom decision edge")
        seen.add(key)
        if item.stance not in ("SUPPORTS", "CONTRADICTS"):
            raise ValueError("only explicit SUPPORTS or CONTRADICTS edges are decisive")
        if key in admitted:
            by_atom[item.atom_id].append(item)
    results: list[AtomicDecision] = []
    for atom_id in atom_ids:
        admitted_items = by_atom[atom_id]
        supports = {item.cluster_id for item in admitted_items if item.stance == "SUPPORTS"}
        contradicts = {item.cluster_id for item in admitted_items if item.stance == "CONTRADICTS"}
        verdict, rule_id = _atomic_verdict(rules, len(supports), len(contradicts))
        if verdict == "SUPPORTED":
            relevant = [item for item in admitted_items if item.stance == "SUPPORTS"]
        elif verdict == "REFUTED":
            relevant = [item for item in admitted_items if item.stance == "CONTRADICTS"]
        else:
            relevant = admitted_items
        robustness, _ = _robustness(rules, relevant)
        results.append(AtomicDecision(
            atom_id, verdict, robustness, len(supports), len(contradicts), _rule_id(rule_id)
        ))
    return results


def adjudicate_composite(atom_verdicts: list[str]) -> CompositeDecision:
    """Apply K1–K5 in contract precedence order; no probabilistic input is accepted."""
    rules, _ = load_rules()
    allowed = set(rules["enums"]["verdict"])
    if not atom_verdicts or any(verdict not in allowed for verdict in atom_verdicts):
        raise ValueError("atom_verdicts must be non-empty valid Judge 2 verdicts")
    for rule in rules["composite_rules"]:
        predicate = rule["when"]
        if predicate == "any_atom_REFUTED" and "REFUTED" in atom_verdicts:
            matched = True
        elif predicate == "otherwise_any_atom_CONFLICTING" and "CONFLICTING" in atom_verdicts:
            matched = True
        elif predicate == "all_atoms_SUPPORTED" and all(v == "SUPPORTED" for v in atom_verdicts):
            matched = True
        elif predicate == "otherwise_any_atom_SUPPORTED" and "SUPPORTED" in atom_verdicts:
            matched = True
        elif predicate == "otherwise":
            matched = True
        else:
            matched = False
        if matched:
            robustness = rule.get("robustness", rule.get("robustness_atoms", "R0"))
            return CompositeDecision(rule["verdict"], robustness, _rule_id(rule["id"]), len(atom_verdicts))
    raise ValueError("composite rules did not produce a decision")
