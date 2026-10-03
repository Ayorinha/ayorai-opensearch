from ayorai_attractor.synthesis import GroundedSynthesizer, validate_claim_citations


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


def test_grounded_synthesizer_abstains_on_unsupported_claim() -> None:
    result = GroundedSynthesizer().synthesize(
        ["claim-a", "claim-b"],
        {"claim-a": ["e1"]},
        {"e1"},
    )
    assert not result.grounding.grounded
    assert result.answer.startswith("ABSTAIN:")


def test_grounded_synthesizer_emits_citation_markers() -> None:
    result = GroundedSynthesizer().synthesize(
        ["claim-a"],
        {"claim-a": ["e1"]},
        {"e1"},
    )
    assert result.grounding.grounded
    assert result.answer == "claim-a [e1]"
