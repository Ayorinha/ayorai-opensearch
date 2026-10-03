from ayorai_attractor.council import CouncilDecision, CouncilVote, CouncilOrchestrator, ProviderParticipant, deliberate, parse_vote_response
from ayorai_attractor.providers.base import Provider, ProviderResponse


def vote(model: str, decision: CouncilDecision) -> CouncilVote:
    return CouncilVote(model, decision, f"{model} rationale")


def test_empty_council_abstains() -> None:
    result = deliberate([])
    assert result.decision is CouncilDecision.ABSTAIN
    assert result.agreement_ratio == 0.0


def test_plurality_is_deterministic() -> None:
    result = deliberate([
        vote("m1", CouncilDecision.VERIFIED),
        vote("m2", CouncilDecision.VERIFIED),
        vote("m3", CouncilDecision.SUPPORTED),
    ])
    assert result.decision is CouncilDecision.VERIFIED
    assert result.agreement_ratio == 2 / 3


def test_tie_abstains_instead_of_using_a_hidden_tiebreaker() -> None:
    result = deliberate([
        vote("m1", CouncilDecision.VERIFIED),
        vote("m2", CouncilDecision.REFUTED),
    ])
    assert result.decision is CouncilDecision.ABSTAIN


class VoteProvider(Provider):
    def __init__(self, text: str) -> None:
        self.text = text

    def execute(self, prompt: str) -> ProviderResponse:
        return ProviderResponse(text=self.text)


def test_provider_adapter_parses_explicit_vote() -> None:
    result = parse_vote_response("m1", ProviderResponse(text="DECISION=refuted\nThe evidence contradicts the claim."))
    assert result.model_id == "m1"
    assert result.decision is CouncilDecision.REFUTED
    assert result.rationale.startswith("The evidence")


def test_provider_adapter_rejects_implicit_vote() -> None:
    provider = ProviderParticipant("m1", VoteProvider("The answer is verified."))
    try:
        provider.vote("test")
    except ValueError as exc:
        assert "DECISION=" in str(exc)
    else:
        raise AssertionError("implicit model output must not become a Council vote")


def test_orchestrator_aggregates_votes_and_isolates_failures() -> None:
    participants = [
        ProviderParticipant("m1", VoteProvider("DECISION=supported\nok")),
        ProviderParticipant("m2", VoteProvider("DECISION=supported\nok")),
        ProviderParticipant("m3", VoteProvider("not structured")),
    ]
    result = CouncilOrchestrator(participants).run("test")
    assert result.result.decision is CouncilDecision.SUPPORTED
    assert result.result.agreement_ratio == 1.0
    assert len(result.result.votes) == 2
    assert len(result.failures) == 1
