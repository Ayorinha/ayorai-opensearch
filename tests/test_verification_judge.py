from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.judge import (
    aggregate_verdict,
    has_complete_provenance,
    judge,
    judge_claim,
)
from ayorai_attractor.verification.models import Claim, Evidence, Stance, StanceEdge, Verdict


def ev(item_id: str, *, origin: str | None, claim_id: str = "c1") -> Evidence:
    return Evidence(
        id=item_id,
        claim_id=claim_id,
        source_id=f"source-{item_id}",
        source_location=f"https://example.test/{item_id}",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        start_offset=0,
        end_offset=10,
        excerpt="factual evidence",
        origin_id=origin,
        canonical_url=None if origin is not None else f"https://example.test/{item_id}",
    )


def edge(item_id: str, stance: Stance) -> StanceEdge:
    return StanceEdge(
        id=f"edge-{item_id}",
        claim_id="c1",
        evidence_id=item_id,
        stance=stance,
    )


def test_judge_table_all_six_rows() -> None:
    claim = Claim(id="c1", text="A claim")
    cases = [
        ([], [], Verdict.UNVERIFIED),
        ([ev("e1", origin="o1")], [edge("e1", Stance.CONTRADICTS)], Verdict.REFUTED),
        (
            [ev("e1", origin="o1"), ev("e2", origin="o2")],
            [edge("e1", Stance.SUPPORTS), edge("e2", Stance.CONTRADICTS)],
            Verdict.CONFLICTING,
        ),
        (
            [ev("e1", origin="o1")],
            [edge("e1", Stance.SUPPORTS)],
            Verdict.PARTIALLY_SUPPORTED,
        ),
        (
            [ev("e1", origin="o1"), ev("e2", origin="o2")],
            [edge("e1", Stance.SUPPORTS), edge("e2", Stance.SUPPORTS)],
            Verdict.VERIFIED,
        ),
        (
            [ev("e1", origin="o1"), ev("e2", origin=None)],
            [edge("e1", Stance.SUPPORTS), edge("e2", Stance.SUPPORTS)],
            Verdict.VERIFIED,
        ),
    ]
    for evidence, stances, expected in cases:
        assert judge_claim(claim, evidence, stances).verdict is expected


def test_dependency_collapses_duplicate_support() -> None:
    claim = Claim(id="c1", text="A claim")
    evidence = [ev("e1", origin="o1"), ev("e2", origin="o1")]
    stances = [edge("e1", Stance.SUPPORTS), edge("e2", Stance.SUPPORTS)]
    result = judge_claim(claim, evidence, stances)
    assert result.support_clusters == 1
    assert result.verdict is Verdict.PARTIALLY_SUPPORTED


def test_provenance_is_complete_for_valid_evidence() -> None:
    assert has_complete_provenance(ev("e1", origin="o1"))


def test_global_precedence_is_deterministic() -> None:
    claim = Claim(id="c1", text="A claim")
    j1 = judge_claim(
        claim,
        [ev("e1", origin="o1")],
        [edge("e1", Stance.CONTRADICTS)],
    )
    j2 = judge_claim(claim, [], [])
    assert aggregate_verdict([j2, j1]) is Verdict.REFUTED


def test_unknown_stance_evidence_does_not_count() -> None:
    claim = Claim(id="c1", text="A claim")
    result = judge_claim(claim, [ev("e1", origin="o1")], [])
    assert result.verdict is Verdict.UNVERIFIED


def test_judge_rejects_duplicate_claim_ids() -> None:
    with pytest.raises(ValueError):
        judge(
            [Claim(id="c1", text="a"), Claim(id="c1", text="b")],
            [],
            [],
        )
