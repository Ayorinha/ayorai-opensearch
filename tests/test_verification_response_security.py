import pytest

from ayorai_attractor.verification.response import ResponseStatus, VerificationResponse
from ayorai_attractor.verification.security import assert_no_secret, contains_secret


def test_no_answer_has_no_verdict() -> None:
    response = VerificationResponse.no_answer("The corpus has no evidence for the requested attribute.")
    assert response.status is ResponseStatus.ABSTAIN_NO_ANSWER
    assert response.verdict is None


def test_out_of_scope_has_no_verdict() -> None:
    response = VerificationResponse.out_of_scope("The question is outside the factual corpus scope.")
    assert response.status is ResponseStatus.ABSTAIN_OUT_OF_SCOPE
    assert response.verdict is None


def test_secret_scanner_covers_nested_response() -> None:
    secret = "TEST-ONLY-EVAL-SECRET"
    response = {"answer": "safe", "evidence": [{"excerpt": secret}]}
    assert contains_secret(response, secret)
    with pytest.raises(ValueError):
        assert_no_secret(response, secret)


def test_secret_scanner_allows_clean_response() -> None:
    assert not contains_secret({"answer": "safe", "evidence": []}, "TEST-ONLY-EVAL-SECRET")
