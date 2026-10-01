from ayorai_attractor.governance import GovernanceConfig, validate_governance


def test_governance_accepts_secure_configuration() -> None:
    result = validate_governance(
        GovernanceConfig("https://example.test", True, True, True, True)
    )
    assert result.passed
    assert result.findings == ()


def test_governance_rejects_insecure_configuration() -> None:
    result = validate_governance(
        GovernanceConfig("http://example.test", False, False, False, False)
    )
    assert not result.passed
    assert len(result.findings) == 5
