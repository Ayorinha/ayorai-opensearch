from __future__ import annotations

from itertools import product

import pytest

from ayorai_attractor.verification.judge2.adjudication import (
    DecisionEvidence,
    _atomic_verdict,
    adjudicate_atoms,
    adjudicate_composite,
)
from ayorai_attractor.verification.judge2.gates import EvidenceDisposition, GateResult
from ayorai_attractor.verification.judge2 import load_rules, rules_sha256


def admitted_fixture(supports: int, contradicts: int) -> tuple[list[DecisionEvidence], GateResult]:
    evidence: list[DecisionEvidence] = []
    dispositions: list[EvidenceDisposition] = []
    for stance, count in (("SUPPORTS", supports), ("CONTRADICTS", contradicts)):
        for index in range(count):
            evidence_id = f"{stance.lower()}-{index}"
            evidence.append(DecisionEvidence(evidence_id, "a1", stance, evidence_id, True))
            dispositions.append(EvidenceDisposition(evidence_id, "a1", True))
    return evidence, GateResult(None, (), True, tuple(dispositions), rules_sha256())


def test_t1_exhaustive_atomic_truth_table_for_cluster_counts_zero_to_five() -> None:
    rules, _ = load_rules()
    for supports, contradicts in product(range(6), repeat=2):
        verdict, rule_id = _atomic_verdict(rules, supports, contradicts)
        if supports == 0 and contradicts == 0:
            assert (verdict, rule_id) == ("UNVERIFIED", "A1")
        elif supports and not contradicts:
            assert (verdict, rule_id) == ("SUPPORTED", "A2")
        elif contradicts and not supports:
            assert (verdict, rule_id) == ("REFUTED", "A3")
        else:
            assert (verdict, rule_id) == ("CONFLICTING", "A4")


def test_atomic_decision_uses_only_gate_admitted_evidence() -> None:
    evidence, gates = admitted_fixture(1, 0)
    rejected = DecisionEvidence("not-admitted", "a1", "CONTRADICTS", "other", True)
    gates = GateResult(None, (), True, gates.evidence + (
        EvidenceDisposition("not-admitted", "a1", False, "EXCERPT_MISMATCH"),
    ), gates.rules_sha256)
    result = adjudicate_atoms(["a1"], evidence + [rejected], gates)[0]
    assert result.verdict == "SUPPORTED"
    assert result.support_clusters == 1
    assert result.contradiction_clusters == 0


def test_atomic_refuses_failed_gate() -> None:
    _, gates = admitted_fixture(0, 0)
    failed = GateResult("ABSTAINED", ("OUT_OF_SCOPE",), False, (), gates.rules_sha256)
    with pytest.raises(ValueError, match="pre-adjudication gates"):
        adjudicate_atoms(["a1"], [], failed)


def test_atomic_rejects_unknown_atom_and_neutral_stance() -> None:
    _, gates = admitted_fixture(0, 0)
    with pytest.raises(ValueError, match="unknown atom"):
        adjudicate_atoms(["a1"], [DecisionEvidence("e", "a2", "SUPPORTS", "c", True)], gates)
    with pytest.raises(ValueError, match="explicit SUPPORTS"):
        adjudicate_atoms(["a1"], [DecisionEvidence("e", "a1", "NEUTRAL", "c", True)], gates)  # type: ignore[arg-type]


def test_t2_exhaustive_composite_truth_table_through_four_atoms() -> None:
    verdicts = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "UNVERIFIED", "CONFLICTING")
    checked = 0
    for size in range(1, 5):
        for values in product(verdicts, repeat=size):
            decision = adjudicate_composite(list(values))
            if "REFUTED" in values:
                assert decision.verdict == "REFUTED"
            elif "CONFLICTING" in values:
                assert decision.verdict == "CONFLICTING"
            elif all(value == "SUPPORTED" for value in values):
                assert decision.verdict == "SUPPORTED"
            elif "SUPPORTED" in values:
                assert decision.verdict == "PARTIALLY_SUPPORTED"
            else:
                assert decision.verdict == "UNVERIFIED"
            checked += 1
    assert checked == sum(5**size for size in range(1, 5))


@pytest.mark.parametrize(
    ("values", "expected", "rule"),
    [
        (["REFUTED", "CONFLICTING"], "REFUTED", "2.0.0/K1"),
        (["CONFLICTING", "SUPPORTED"], "CONFLICTING", "2.0.0/K2"),
        (["SUPPORTED", "SUPPORTED"], "SUPPORTED", "2.0.0/K3"),
        (["SUPPORTED", "UNVERIFIED"], "PARTIALLY_SUPPORTED", "2.0.0/K4"),
        (["UNVERIFIED", "PARTIALLY_SUPPORTED"], "UNVERIFIED", "2.0.0/K5"),
    ],
)
def test_t3_composite_precedence_and_rule_trace(
    values: list[str], expected: str, rule: str
) -> None:
    decision = adjudicate_composite(values)
    assert decision.verdict == expected
    assert decision.rule_id == rule


def test_t4_composite_rejects_empty_or_unknown_verdict() -> None:
    with pytest.raises(ValueError):
        adjudicate_composite([])
    with pytest.raises(ValueError):
        adjudicate_composite(["MODEL_SAYS_SUPPORTED"])


def test_t5_rules_are_loaded_from_contract_and_ids_are_versioned() -> None:
    rules, _ = load_rules()
    assert {item["id"] for item in rules["atomic_rules"]} == {"A1", "A2", "A3", "A4"}
    assert {item["id"] for item in rules["robustness_rules"]} == {"R0", "R1", "R2", "R3"}
    assert {item["id"] for item in rules["composite_rules"]} == {"K1", "K2", "K3", "K4", "K5"}
    assert adjudicate_composite(["SUPPORTED"]).rule_id.startswith("2.0.0/")


def test_t6_robustness_is_diagnostic_and_does_not_change_atomic_verdict() -> None:
    single, single_gate = admitted_fixture(1, 0)
    many, many_gate = admitted_fixture(2, 0)
    single_result = adjudicate_atoms(["a1"], single, single_gate)[0]
    many_result = adjudicate_atoms(["a1"], many, many_gate)[0]
    assert single_result.verdict == many_result.verdict == "SUPPORTED"
    assert single_result.robustness == "R1"
    assert many_result.robustness == "R3"
