from __future__ import annotations

from datetime import UTC, datetime
from itertools import product

import pytest

from ayorai_attractor.verification.judge2.adjudication import (
    AtomicDecision,
    DecisionEvidence,
    _atomic_verdict,
    adjudicate_atoms,
    adjudicate_composite,
)
from ayorai_attractor.verification.judge2.gates import EvidenceDisposition, GateResult
from ayorai_attractor.verification.judge2 import adjudication, load_rules, rules_sha256
from ayorai_attractor.verification.models import Evidence

VERDICTS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "UNVERIFIED", "CONFLICTING")
ROBUSTNESS = ("R0", "R1", "R2", "R3")


def source(item_id: str, *, origin: str | None = None, complete: bool = True) -> Evidence:
    return Evidence(
        id=item_id,
        claim_id="c1",
        source_id=f"source-{item_id}",
        source_location=f"https://example.test/{item_id}",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        start_offset=0,
        end_offset=1,
        excerpt="x",
        origin_id=origin or f"origin-{item_id}",
        provenance_complete=complete,
    )


def fixture(
    stances: list[tuple[str, str, str]],
    *,
    origins: dict[str, str] | None = None,
    incomplete: set[str] | None = None,
) -> tuple[list[DecisionEvidence], GateResult]:
    declared: list[DecisionEvidence] = []
    dispositions: list[EvidenceDisposition] = []
    for evidence_id, atom_id, stance in stances:
        item = source(
            evidence_id,
            origin=(origins or {}).get(evidence_id),
            complete=evidence_id not in (incomplete or set()),
        )
        declared.append(DecisionEvidence(evidence_id, atom_id, stance))  # type: ignore[arg-type]
        dispositions.append(
            EvidenceDisposition(
                evidence_id,
                atom_id,
                True,
                None,
                stance,
                item,
            )
        )
    gates = GateResult(None, (), True, tuple(dispositions), rules_sha256())
    return declared, gates


def atomic(
    atom_id: str,
    verdict: str,
    robustness: str,
    support: str = "R0",
    contradiction: str = "R0",
) -> AtomicDecision:
    return AtomicDecision(
        atom_id=atom_id,
        verdict=verdict,
        robustness=robustness,
        robustness_support=support,
        robustness_contradiction=contradiction,
        support_clusters=0,
        contradiction_clusters=0,
        rule_id="2.0.0/A1",
    )


def test_t1_atomic_truth_table_covers_support_zero_to_three_and_contradiction_zero_to_two() -> None:
    rules, _ = load_rules()
    for supports, contradicts in product(range(4), range(3)):
        verdict, rule_id = _atomic_verdict(rules, supports, contradicts)
        if supports == 0 and contradicts == 0:
            assert (verdict, rule_id) == ("UNVERIFIED", "A1")
        elif supports and not contradicts:
            assert (verdict, rule_id) == ("SUPPORTED", "A2")
        elif contradicts and not supports:
            assert (verdict, rule_id) == ("REFUTED", "A3")
        else:
            assert (verdict, rule_id) == ("CONFLICTING", "A4")


def test_t1_provenance_selects_r2_or_r3_without_changing_verdict() -> None:
    complete, gates_complete = fixture([
        ("s1", "a1", "SUPPORTS"), ("s2", "a1", "SUPPORTS"),
    ])
    incomplete, gates_incomplete = fixture(
        [("s1", "a1", "SUPPORTS"), ("s2", "a1", "SUPPORTS")],
        incomplete={"s2"},
    )
    good = adjudicate_atoms(["a1"], complete, gates_complete)[0]
    uncertain = adjudicate_atoms(["a1"], incomplete, gates_incomplete)[0]
    assert good.verdict == uncertain.verdict == "SUPPORTED"
    assert good.robustness == "R3"
    assert uncertain.robustness == "R2"


def test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms() -> None:
    checked = 0
    for size in range(1, 5):
        for values in product(VERDICTS, repeat=size):
            decisions = [atomic(str(index), value, "R0") for index, value in enumerate(values)]
            result = adjudicate_composite(decisions)
            if "REFUTED" in values:
                assert result.verdict == "REFUTED"
            elif "CONFLICTING" in values:
                assert result.verdict == "CONFLICTING"
            elif all(value == "SUPPORTED" for value in values):
                assert result.verdict == "SUPPORTED"
            elif "SUPPORTED" in values:
                assert result.verdict == "PARTIALLY_SUPPORTED"
            else:
                assert result.verdict == "UNVERIFIED"
            assert result.robustness in ROBUSTNESS
            checked += 1
    assert checked == sum(5**size for size in range(1, 5)) == 780


def test_t3_single_atomic_verdict_never_partially_supported() -> None:
    declared, gates = fixture([("s1", "a1", "SUPPORTS")])
    decision = adjudicate_atoms(["a1"], declared, gates)[0]
    assert decision.verdict == "SUPPORTED"
    assert decision.verdict != "PARTIALLY_SUPPORTED"


def test_t4_increasing_support_clusters_does_not_change_supported_verdict() -> None:
    one, one_gate = fixture([("s1", "a1", "SUPPORTS")])
    many, many_gate = fixture([
        ("s1", "a1", "SUPPORTS"), ("s2", "a1", "SUPPORTS"),
        ("s3", "a1", "SUPPORTS"),
    ])
    first = adjudicate_atoms(["a1"], one, one_gate)[0]
    later = adjudicate_atoms(["a1"], many, many_gate)[0]
    assert first.verdict == later.verdict == "SUPPORTED"
    assert later.support_clusters >= first.support_clusters


def test_t5_republication_with_same_origin_does_not_increase_support_clusters() -> None:
    declared, gates = fixture(
        [("s1", "a1", "SUPPORTS"), ("s2", "a1", "SUPPORTS")],
        origins={"s1": "shared-origin", "s2": "shared-origin"},
    )
    result = adjudicate_atoms(["a1"], declared, gates)[0]
    assert result.support_clusters == 1
    assert result.robustness == "R1"


def test_only_gate_admitted_evidence_contributes_to_verdict() -> None:
    declared, gates = fixture([("s1", "a1", "SUPPORTS")])
    rejected_source = source("bad")
    rejected = EvidenceDisposition(
        "bad", "a1", False, "EXCERPT_MISMATCH", "CONTRADICTS", rejected_source
    )
    declared.append(DecisionEvidence("bad", "a1", "CONTRADICTS"))
    gates = GateResult(None, (), True, gates.evidence + (rejected,), gates.rules_sha256)
    result = adjudicate_atoms(["a1"], declared, gates)[0]
    assert result.verdict == "SUPPORTED"
    assert result.support_clusters == 1
    assert result.contradiction_clusters == 0


def test_gate_validated_stance_cannot_be_overridden_by_caller() -> None:
    declared, gates = fixture([("e1", "a1", "CONTRADICTS")])
    declared[0] = DecisionEvidence("e1", "a1", "SUPPORTS")
    with pytest.raises(ValueError, match="stance differs"):
        adjudicate_atoms(["a1"], declared, gates)


def test_conflicting_atomic_decision_exposes_both_sides_and_uses_minimum() -> None:
    declared, gates = fixture([
        ("s1", "a1", "SUPPORTS"),
        ("s2", "a1", "SUPPORTS"),
        ("c1", "a1", "CONTRADICTS"),
    ])
    result = adjudicate_atoms(["a1"], declared, gates)[0]
    assert result.verdict == "CONFLICTING"
    assert result.robustness_support == "R3"
    assert result.robustness_contradiction == "R1"
    assert result.robustness == "R1"


def test_composite_robustness_is_minimum_of_atoms_selected_by_rule() -> None:
    refuted = adjudicate_composite([
        atomic("a1", "REFUTED", "R1"),
        atomic("a2", "SUPPORTED", "R3"),
    ])
    supported = adjudicate_composite([
        atomic("a1", "SUPPORTED", "R3"),
        atomic("a2", "SUPPORTED", "R2"),
    ])
    conflicting = adjudicate_composite([atomic("a1", "CONFLICTING", "R1")])
    assert (refuted.verdict, refuted.robustness) == ("REFUTED", "R1")
    assert (supported.verdict, supported.robustness) == ("SUPPORTED", "R2")
    assert (conflicting.verdict, conflicting.robustness) == ("CONFLICTING", "R1")
    assert all(item.robustness in ROBUSTNESS for item in (refuted, supported, conflicting))


def test_t6_composite_result_is_invariant_to_input_order() -> None:
    decisions = [
        atomic("a1", "SUPPORTED", "R3"),
        atomic("a2", "UNVERIFIED", "R1"),
        atomic("a3", "SUPPORTED", "R2"),
    ]
    assert adjudicate_composite(decisions) == adjudicate_composite(list(reversed(decisions)))


def test_t6_precedence_uses_contract_order_even_if_rule_list_is_shuffled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rules, digest = load_rules()
    rules["composite_rules"] = list(reversed(rules["composite_rules"]))
    monkeypatch.setattr(adjudication, "load_rules", lambda: (rules, digest))
    result = adjudicate_composite([
        atomic("a1", "REFUTED", "R1"),
        atomic("a2", "CONFLICTING", "R3"),
    ])
    assert result.verdict == "REFUTED"
    assert result.rule_id == "2.0.0/K1"


def test_t6_order_of_evidence_does_not_change_atomic_result() -> None:
    edges = [
        ("s1", "a1", "SUPPORTS"),
        ("s2", "a1", "SUPPORTS"),
        ("c1", "a1", "CONTRADICTS"),
    ]
    declared, gates = fixture(edges)
    reversed_declared, reversed_gates = fixture(list(reversed(edges)))
    assert adjudicate_atoms(["a1"], declared, gates)[0] == adjudicate_atoms(
        ["a1"], reversed_declared, reversed_gates
    )[0]


def test_contract_rule_ids_are_versioned_and_robustness_enum_is_closed() -> None:
    rules, _ = load_rules()
    assert {item["id"] for item in rules["atomic_rules"]} == {"A1", "A2", "A3", "A4"}
    assert {item["id"] for item in rules["robustness_rules"]} == {"R0", "R1", "R2", "R3"}
    assert {item["id"] for item in rules["composite_rules"]} == {"K1", "K2", "K3", "K4", "K5"}
    with pytest.raises(ValueError, match="robustness enum"):
        adjudicate_composite([atomic("a1", "SUPPORTED", "R9")])
