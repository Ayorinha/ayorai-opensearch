"""Contract-driven deterministic atomic and composite adjudication for Judge 2.0.0.

Only gate-admitted, validated evidence can contribute. Clusters and provenance
are derived from the validated Evidence objects carried by GateResult.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import MappingProxyType
from typing import Any, Literal

import rfc8785

from ayorai_attractor.verification.clusters import cluster_evidence
from ayorai_attractor.verification.models import Evidence

from . import canonical_json_bytes, load_rules
from .gates import GateResult, evaluate_gates

Stance = Literal["SUPPORTS", "CONTRADICTS"]
EXPECTED_RULES_SHA256 = "493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc"
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


def _adjudicate_atoms(
    atom_ids: list[str],
    evidence: list[DecisionEvidence],
    gates: GateResult,
) -> list[AtomicDecision]:
    """Adjudicate using gate-validated stance and provenance, never caller metadata."""
    rules, contract_sha256 = load_rules()
    if contract_sha256 != EXPECTED_RULES_SHA256:
        raise ValueError("loaded Judge contract hash differs from the pinned contract")
    if gates.rules_sha256 != contract_sha256:
        raise ValueError("GateResult rules hash does not match the loaded Judge contract")
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


def _adjudicate_composite(atom_decisions: list[AtomicDecision]) -> CompositeDecision:
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


@dataclass(frozen=True)
class AdjudicationResult:
    """Canonical, deterministic public output of Judge 2.0.0."""

    judge_rules_version: str
    decision_state: str
    reason_codes: tuple[str, ...]
    rules_sha256: str
    input_sha256: str
    verdict: str | None
    coverage: Mapping[str, int]
    robustness: str
    atoms: tuple[Mapping[str, Any], ...]
    rule_trace: tuple[Mapping[str, str], ...]
    output_sha256: str
    atomic_decisions: tuple[AtomicDecision, ...]
    composite_decision: CompositeDecision | None

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical result object, including its output digest."""
        return {
            "judge_rules_version": self.judge_rules_version,
            "rules_sha256": self.rules_sha256,
            "input_sha256": self.input_sha256,
            "decision_state": self.decision_state,
            "reason_codes": list(self.reason_codes),
            "verdict": self.verdict,
            "coverage": _deep_thaw(self.coverage),
            "robustness": self.robustness,
            "atoms": [_deep_thaw(atom) for atom in self.atoms],
            "rule_trace": [_deep_thaw(item) for item in self.rule_trace],
            "output_sha256": self.output_sha256,
        }

    def canonical_bytes(self) -> bytes:
        """Serialize the complete result using ADR-009's canonical UTF-8 JSON."""
        from . import canonical_json_bytes

        return canonical_json_bytes(self.to_dict())


def _deep_freeze(value: Any) -> Any:
    """Recursively freeze mappings and sequences so hashed results cannot drift."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: Any) -> Any:
    """Return fresh JSON-compatible containers from an immutable result."""
    if isinstance(value, Mapping):
        return {key: _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_thaw(item) for item in value]
    return value


def verify_output(result_dict: Mapping[str, Any]) -> bool:
    """Verify output_sha256 against canonical JSON excluding the digest field."""
    if not isinstance(result_dict, Mapping):
        return False
    digest = result_dict.get("output_sha256")
    if not isinstance(digest, str):
        return False
    payload = {key: value for key, value in result_dict.items() if key != "output_sha256"}
    try:
        from . import canonical_json_bytes

        actual = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    except (TypeError, ValueError):
        return False
    return actual == digest


def _json_safe(value: Any, *, allow_unsupported: bool = False) -> Any:
    """Convert explicitly supported values to stable JSON-compatible values."""
    if hasattr(value, "model_dump"):
        return _json_safe(
            value.model_dump(mode="python"),
            allow_unsupported=allow_unsupported,
        )
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            if allow_unsupported:
                return {
                    "unsupported_type": "datetime.naive",
                    "representation": value.isoformat(),
                }
            raise TypeError(
                "naive datetime is not supported; provide an explicit timezone"
            )
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            if allow_unsupported:
                raise TypeError("canonical JSON objects require string keys")
            raise TypeError("canonical JSON objects require string keys")
        return {
            key: _json_safe(item, allow_unsupported=allow_unsupported)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, allow_unsupported=allow_unsupported) for item in value]
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9007199254740991 and allow_unsupported:
            return {
                "unsupported_type": "rfc8785.integer_out_of_range",
                "representation": str(value),
            }
        return value
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            if allow_unsupported:
                return {
                    "unsupported_type": "builtins.float",
                    "representation": (
                        "nan" if math.isnan(value) else ("+inf" if value > 0 else "-inf")
                    ),
                }
            raise TypeError("non-finite floats are not supported in canonical JSON")
        return value
    if allow_unsupported:
        try:
            representation = repr(value)
        except Exception:
            representation = "<repr-unavailable>"
        return {
            "unsupported_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "representation": representation,
        }
    raise TypeError(
        f"unsupported input type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _canonical_input(
    request: Mapping[str, Any], *, allow_unsupported: bool = False
) -> dict[str, Any]:
    """Normalize order-insensitive collections before hashing the request."""
    payload = _json_safe(request, allow_unsupported=allow_unsupported)
    if not isinstance(payload, dict):
        raise TypeError("canonical input must be a JSON object")
    for field, keys in (
        ("atoms", ("id",)),
        ("evidence", ("id",)),
        ("stances", ("atom_id", "evidence_id", "id")),
    ):
        items = payload.get(field)
        if isinstance(items, list):
            payload[field] = sorted(
                items,
                key=lambda item: tuple(str(item.get(key, "")) for key in keys)
                if isinstance(item, Mapping) else ("",),
            )
    return payload


def _build_result(
    *,
    request: Mapping[str, Any],
    decision_state: str,
    reason_codes: tuple[str, ...],
    rules_sha256: str,
    atomic_decisions: tuple[AtomicDecision, ...] = (),
    composite_decision: CompositeDecision | None = None,
    gates: GateResult | None = None,
    input_sha256_override: str | None = None,
) -> AdjudicationResult:
    """Build and hash a canonical result; the output digest excludes itself."""
    from . import canonical_json_bytes

    if input_sha256_override is None:
        canonical_input = canonical_json_bytes(_canonical_input(request))
        input_digest = hashlib.sha256(canonical_input).hexdigest()
    else:
        input_digest = input_sha256_override
    if decision_state == "DECIDED":
        if composite_decision is None:
            raise ValueError("DECIDED result must contain a composite decision")
        verdict = composite_decision.verdict
        atom_by_id = {item.atom_id: item for item in atomic_decisions}
        dispositions = gates.evidence if gates is not None else ()
        output_atoms: list[dict[str, Any]] = []
        for atom_id in sorted(atom_by_id):
            decision = atom_by_id[atom_id]
            admitted: list[dict[str, str]] = []
            excluded: list[dict[str, str]] = []
            for item in dispositions:
                if item.atom_id != atom_id:
                    continue
                if item.admitted:
                    admitted.append({
                        "id": item.evidence_id,
                        "stance": item.stance or "",
                    })
                else:
                    excluded.append({
                        "id": item.evidence_id,
                        "reason": item.reason or "UNKNOWN_EXCLUSION",
                    })
            output_atoms.append({
                "atom_id": decision.atom_id,
                "verdict": decision.verdict,
                "support_clusters": decision.support_clusters,
                "contradiction_clusters": decision.contradiction_clusters,
                "robustness": decision.robustness,
                "rule_id": decision.rule_id,
                "admitted_evidence": sorted(
                    admitted, key=lambda item: (item["id"], item["stance"])
                ),
                "excluded_evidence": sorted(
                    excluded, key=lambda item: (item["id"], item["reason"])
                ),
            })
        counts = {name: 0 for name in (
            "supported", "refuted", "conflicting", "unverified"
        )}
        for decision in atomic_decisions:
            key = decision.verdict.lower()
            if key in counts:
                counts[key] += 1
        coverage = {**counts, "total": len(atomic_decisions)}
        robustness = composite_decision.robustness
        trace = [
            {"rule_id": item.rule_id, "label": "atomic"}
            for item in sorted(atomic_decisions, key=lambda item: item.atom_id)
        ]
        trace.append({"rule_id": composite_decision.rule_id, "label": "derived"})
    else:
        if decision_state not in {"ABSTAINED", "INVALID_INPUT"}:
            raise ValueError(f"unsupported decision state: {decision_state}")
        verdict = None
        output_atoms = []
        coverage = {
            "supported": 0, "refuted": 0, "conflicting": 0,
            "unverified": 0, "total": 0,
        }
        robustness = "R0"
        rules, _ = load_rules()
        section = "input_gate" if decision_state == "INVALID_INPUT" else "abstention"
        entries_by_code = {item["code"]: item for item in rules[section]}
        trace = [
            {"rule_id": entries_by_code[code]["rule_id"], "label": "gate"}
            for code in reason_codes
            if code in entries_by_code
        ]

    base: dict[str, Any] = {
        "judge_rules_version": "2.0.0",
        "rules_sha256": rules_sha256,
        "input_sha256": input_digest,
        "decision_state": decision_state,
        "reason_codes": list(reason_codes),
        "verdict": verdict,
        "coverage": coverage,
        "robustness": robustness,
        "atoms": output_atoms,
        "rule_trace": trace,
    }
    output_digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    return AdjudicationResult(
        judge_rules_version="2.0.0",
        decision_state=decision_state,
        reason_codes=reason_codes,
        rules_sha256=rules_sha256,
        input_sha256=input_digest,
        verdict=verdict,
        coverage=_deep_freeze(coverage),
        robustness=robustness,
        atoms=tuple(_deep_freeze(atom) for atom in output_atoms),
        rule_trace=tuple(_deep_freeze(item) for item in trace),
        output_sha256=output_digest,
        atomic_decisions=atomic_decisions,
        composite_decision=composite_decision,
    )


def adjudicate(request: Mapping[str, Any]) -> AdjudicationResult:
    """Validate a request, run gates internally, then issue deterministic decisions.

    Callers provide evidence and source text, never a GateResult or a verdict.
    """
    if not isinstance(request, Mapping):
        raise TypeError("request must be a mapping")
    required = {
        "protocol_version", "claim_id", "claim_text", "atoms",
        "evidence", "stances", "source_texts",
    }
    optional = {
        "out_of_scope", "factual_claim", "temporal_anchor_present",
        "retrieval_succeeded", "evidence_pool_integrity_ok",
    }
    unknown = set(request) - required - optional
    missing = required - set(request)
    if unknown or missing:
        raise ValueError(
            f"invalid adjudication request fields: unknown={sorted(unknown)}, "
            f"missing={sorted(missing)}"
        )
    gate_input = {key: request[key] for key in required | (set(request) & optional)}
    try:
        canonical_json_bytes(_canonical_input(request))
    except (TypeError, rfc8785.IntegerDomainError, rfc8785.FloatDomainError):
        # RFC 8785 rejects numbers outside its interoperable IEEE-754 domain.
        # Re-encode the rejected value as a marker so the Judge can return a
        # deterministic SCHEMA_VIOLATION instead of leaking an exception.
        rejection_input = canonical_json_bytes(
            _canonical_input(request, allow_unsupported=True)
        )
        _, contract_sha256 = load_rules()
        return _build_result(
            request=request,
            decision_state="INVALID_INPUT",
            reason_codes=("SCHEMA_VIOLATION",),
            rules_sha256=contract_sha256,
            input_sha256_override=hashlib.sha256(rejection_input).hexdigest(),
        )
    gates = evaluate_gates(**gate_input)
    _, contract_sha256 = load_rules()
    if contract_sha256 != EXPECTED_RULES_SHA256:
        raise ValueError("loaded Judge contract hash differs from the pinned contract")
    if gates.rules_sha256 != contract_sha256:
        raise ValueError("GateResult rules hash does not match the loaded Judge contract")
    if gates.decision_state is not None:
        return _build_result(
            request=request,
            decision_state=gates.decision_state,
            reason_codes=gates.reason_codes,
            rules_sha256=contract_sha256,
            gates=gates,
        )

    raw_atoms = request["atoms"]
    atom_ids = [str(atom["id"]) for atom in raw_atoms]
    declared: list[DecisionEvidence] = []
    for stance in request["stances"]:
        relation = str(stance["stance"]).upper()
        if relation in ("SUPPORTS", "CONTRADICTS"):
            declared.append(
                DecisionEvidence(
                    evidence_id=str(stance["evidence_id"]),
                    atom_id=str(stance["atom_id"]),
                    stance=relation,  # type: ignore[arg-type]
                )
            )
    atomic = _adjudicate_atoms(atom_ids, declared, gates)
    composite = _adjudicate_composite(atomic)
    return _build_result(
        request=request,
        decision_state="DECIDED",
        reason_codes=(),
        rules_sha256=contract_sha256,
        atomic_decisions=tuple(atomic),
        composite_decision=composite,
        gates=gates,
    )


__all__ = [
    "AdjudicationResult",
    "AtomicDecision",
    "CompositeDecision",
    "DecisionEvidence",
    "adjudicate",
]
