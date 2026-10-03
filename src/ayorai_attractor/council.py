"""Controlled multi-model Council for R3.

Providers may propose explicit votes, but the Council only aggregates those
votes. No provider is authoritative and no hidden model is used as a judge.
"""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ayorai_attractor.providers.base import Provider, ProviderResponse


class CouncilDecision(StrEnum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"
    REFUTED = "refuted"
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


@dataclass(frozen=True)
class CouncilRunResult:
    result: CouncilResult
    failures: tuple[str, ...]


class VoteParticipant(Protocol):
    model_id: str

    def vote(self, prompt: str) -> CouncilVote:
        ...


class ProviderParticipant:
    """Adapter from a Provider to the explicit Council vote contract.

    The provider must return a response beginning with DECISION=<state>.
    Everything after the first line is retained only as rationale text.
    """

    def __init__(self, model_id: str, provider: Provider) -> None:
        self.model_id = model_id
        self.provider = provider

    def vote(self, prompt: str) -> CouncilVote:
        response = self.provider.execute(prompt)
        return parse_vote_response(self.model_id, response)


def parse_vote_response(model_id: str, response: ProviderResponse) -> CouncilVote:
    first, _, rationale = response.text.partition("\n")
    prefix = "DECISION="
    if not first.startswith(prefix):
        raise ValueError("Council response must start with DECISION=<state>")
    raw = first.removeprefix(prefix).strip().lower()
    allowed = {
        item.value for item in CouncilDecision if item is not CouncilDecision.ABSTAIN
    }
    if raw not in allowed:
        raise ValueError(f"unsupported Council decision: {raw}")
    return CouncilVote(model_id, CouncilDecision(raw), rationale.strip())


def deliberate(votes: list[CouncilVote]) -> CouncilResult:
    """Return deterministic plurality; ties and empty votes abstain."""
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


class CouncilOrchestrator:
    """Run independent participants and aggregate only explicit votes."""

    def __init__(self, participants: list[VoteParticipant]) -> None:
        if not participants:
            raise ValueError("at least one Council participant is required")
        self.participants = tuple(participants)

    def run(self, prompt: str) -> CouncilRunResult:
        votes: list[CouncilVote] = []
        failures: list[str] = []
        for participant in self.participants:
            try:
                votes.append(participant.vote(prompt))
            except Exception as exc:
                failures.append(f"{participant.model_id}: {exc}")
        return CouncilRunResult(deliberate(votes), tuple(failures))
