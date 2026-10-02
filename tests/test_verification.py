from datetime import datetime, timezone

from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.models import Claim, Evidence, Stance, StanceEdge, Verdict


def _evidence(
    evidence_id: str,
    claim_id: str = "c1",
    *,
    origin_id: str,
    start: int = 0,
    end: int = 20,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        claim_id=claim_id,
        source_id=origin_id,
        source_location=f"doc:{evidence_id}",
        retrieved_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        start_offset=start,
        end_offset=end,
        excerpt="The claim is supported.",
        origin_id=origin_id,
    )


def test_judge_verifies_two_independent_supporting_clusters() -> None:
    claims = [Claim(id="c1", text="The claim is true.")]
    evidence = [_evidence("e1", origin_id="origin-a"), _evidence("e2", origin_id="origin-b")]
    stances = [
        StanceEdge(id="s1", claim_id="c1", evidence_id="e1", stance=Stance.SUPPORTS),
        StanceEdge(id="s2", claim_id="c1", evidence_id="e2", stance=Stance.SUPPORTS),
    ]

    judgments, verdict = judge(claims, evidence, stances)

    assert verdict is Verdict.VERIFIED
    assert judgments[0].support_clusters == 2
    assert judgments[0].provenance_complete is True


def test_judge_refutes_claim_with_only_contradicting_evidence() -> None:
    claims = [Claim(id="c1", text="The claim is true.")]
    evidence = [_evidence("e1", origin_id="origin-a")]
    stances = [
        StanceEdge(id="s1", claim_id="c1", evidence_id="e1", stance=Stance.CONTRADICTS),
    ]

    judgments, verdict = judge(claims, evidence, stances)

    assert verdict is Verdict.REFUTED
    assert judgments[0].contradiction_clusters == 1


def test_judge_prioritizes_conflict_over_support() -> None:
    claims = [Claim(id="c1", text="The claim is true.")]
    evidence = [_evidence("e1", origin_id="origin-a"), _evidence("e2", origin_id="origin-b")]
    stances = [
        StanceEdge(id="s1", claim_id="c1", evidence_id="e1", stance=Stance.SUPPORTS),
        StanceEdge(id="s2", claim_id="c1", evidence_id="e2", stance=Stance.CONTRADICTS),
    ]

    judgments, verdict = judge(claims, evidence, stances)

    assert verdict is Verdict.CONFLICTING
    assert judgments[0].support_clusters == 1
    assert judgments[0].contradiction_clusters == 1
