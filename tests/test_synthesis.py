from ayorai_attractor.synthesis import validate_claim_citations


def test_grounding_gate_accepts_claims_with_known_citations() -> None:
    result = validate_claim_citations(
        ["claim-a", "claim-b"],
        {"claim-a": ["e1"], "claim-b": ["e2"]},
        {"e1", "e2"},
    )
    assert result.grounded


def test_grounding_gate_rejects_missing_or_unknown_citations() -> None:
    result = validate_claim_citations(
        ["claim-a", "claim-b"],
        {"claim-a": ["missing"]},
        {"e1"},
    )
    assert not result.grounded
    assert result.unsupported_claims == ("claim-a", "claim-b")
