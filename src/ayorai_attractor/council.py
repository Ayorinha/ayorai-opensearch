"""Deterministic multi-model Council core for R3.

Models provide explicit votes; this module only aggregates those votes.
No model is treated as authoritative and no hidden tie-breaker exists.
"""

from dataclasses import dataclass
from enum import StrEnum
from collections import Counter


class CouncilDecision(StrEnum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class CouncilVote:
    model_id: str
    decision: CouncilDecision
    rationale: str


@dataclass(frozen=True)
class CouncilResult:
    decision: CouncilDecision
    votes: tuple[CouncilVote, ...]
    agreement_ratio: float


def deliberate(votes: list[CouncilVote]) -> CouncilResult:
    """Return a deterministic plurality result; ties and empty votes abstain."""
    if not votes:
        return CouncilResult(CouncilDecision.ABSTAIN, (), 0.0)

    counts = Counter(vote.decision for vote in votes)
    highest = max(counts.values())
    winners = sorted(
        decision.value for decision, count in counts.items() if count == highest
    )
    if len(winners) != 1:
        return CouncilResult(
            CouncilDecision.ABSTAIN,
            tuple(votes),
            highest / len(votes),
        )

    decision = CouncilDecision(winners[0])
    return CouncilResult(
        decision,
        tuple(votes),
        counts[decision] / len(votes),
    )
