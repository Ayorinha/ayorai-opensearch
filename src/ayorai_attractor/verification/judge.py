"""Deterministic Judge rules from ADR-002.

The Judge consumes structured claims, evidence, and explicit stance edges.
No language model is consulted and no model output can choose the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .clusters import cluster_evidence
from .models import Claim, Evidence, Stance, StanceEdge, Verdict

_GLOBAL_PRECEDENCE: tuple[Verdict, ...] = (
    Verdict.REFUTED,
    Verdict.CONFLICTING,
    Verdict.UNVERIFIED,
    Verdict.PARTIALLY_SUPPORTED,
    Verdict.SUPPORTED,
    Verdict.VERIFIED,
)


@dataclass(frozen=True)
class ClaimJudgment:
    claim_id: str
    support_clusters: int
    contradiction_clusters: int
    provenance_complete: bool
    verdict: Verdict


def has_complete_provenance(evidence: Evidence) -> bool:
    """Return whether one evidence item satisfies ADR-002 §2."""
    if not evidence.source_id or not evidence.source_location:
        return False
    if not isinstance(evidence.retrieved_at, datetime):
        return False
    if evidence.start_offset < 0 or evidence.end_offset <= evidence.start_offset:
        return False
    if not evidence.excerpt.strip():
        return False
    return evidence.origin_id is not None or evidence.canonical_url is not None


def judge_claim(
    claim: Claim,
    evidence: list[Evidence],
    stances: list[StanceEdge],
) -> ClaimJudgment:
    """Apply the six-row ADR-002 table to exactly one claim."""
    by_id = {item.id: item for item in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("evidence ids must be unique")

    claim_evidence = [
        item for item in evidence if item.claim_id == claim.id
    ]
    stance_by_evidence: dict[str, Stance] = {}
    for edge in stances:
        if edge.claim_id != claim.id:
            continue
        if edge.evidence_id not in by_id:
            raise ValueError(f"stance references unknown evidence: {edge.evidence_id}")
        if edge.evidence_id in stance_by_evidence:
            raise ValueError(f"multiple stances for evidence: {edge.evidence_id}")
        stance_by_evidence[edge.evidence_id] = edge.stance

    supporting = [
        item for item in claim_evidence
        if stance_by_evidence.get(item.id) is Stance.SUPPORTS
    ]
    contradicting = [
        item for item in claim_evidence
        if stance_by_evidence.get(item.id) is Stance.CONTRADICTS
    ]
    support_clusters = len(cluster_evidence(supporting))
    contradiction_clusters = len(cluster_evidence(contradicting))
    provenance_complete = bool(supporting) and all(
        has_complete_provenance(item) for item in supporting
    )

    if support_clusters == 0 and contradiction_clusters == 0:
        verdict = Verdict.UNVERIFIED
    elif support_clusters == 0:
        verdict = Verdict.REFUTED
    elif contradiction_clusters:
        verdict = Verdict.CONFLICTING
    elif support_clusters == 1:
        verdict = Verdict.PARTIALLY_SUPPORTED
    elif not provenance_complete:
        verdict = Verdict.SUPPORTED
    else:
        verdict = Verdict.VERIFIED

    return ClaimJudgment(
        claim_id=claim.id,
        support_clusters=support_clusters,
        contradiction_clusters=contradiction_clusters,
        provenance_complete=provenance_complete,
        verdict=verdict,
    )


def aggregate_verdict(judgments: list[ClaimJudgment]) -> Verdict:
    """Apply ADR-002 §4 global precedence without any heuristic weighting."""
    if not judgments:
        raise ValueError("at least one claim judgment is required")
    present = {item.verdict for item in judgments}
    for verdict in _GLOBAL_PRECEDENCE:
        if verdict in present:
            return verdict
    raise AssertionError("all Verdict states must be covered by precedence")


def judge(
    claims: list[Claim],
    evidence: list[Evidence],
    stances: list[StanceEdge],
) -> tuple[list[ClaimJudgment], Verdict]:
    """Judge all claims and return per-claim plus global deterministic results."""
    claim_ids = {claim.id for claim in claims}
    if len(claim_ids) != len(claims):
        raise ValueError("claim ids must be unique")
    if any(edge.claim_id not in claim_ids for edge in stances):
        raise ValueError("stance references unknown claim")
    judgments = [judge_claim(claim, evidence, stances) for claim in claims]
    return judgments, aggregate_verdict(judgments)
