from ayorai_attractor.council import CouncilDecision, CouncilVote, deliberate


def vote(model: str, decision: CouncilDecision) -> CouncilVote:
    return CouncilVote(model, decision, f"{model} rationale")


def test_empty_council_abstains() -> None:
    result = deliberate([])
    assert result.decision is CouncilDecision.ABSTAIN
    assert result.agreement_ratio == 0.0


def test_plurality_is_deterministic() -> None:
    result = deliberate(
        [
            vote("m1", CouncilDecision.VERIFIED),
            vote("m2", CouncilDecision.VERIFIED),
            vote("m3", CouncilDecision.SUPPORTED),
        ]
    )
    assert result.decision is CouncilDecision.VERIFIED
    assert result.agreement_ratio == 2 / 3


def test_tie_abstains_instead_of_using_a_hidden_tiebreaker() -> None:
    result = deliberate(
        [
            vote("m1", CouncilDecision.VERIFIED),
            vote("m2", CouncilDecision.REFUTED)
            if hasattr(CouncilDecision, "REFUTED")
            else vote("m2", CouncilDecision.CONFLICTING),
        ]
    )
    assert result.decision is CouncilDecision.ABSTAIN
