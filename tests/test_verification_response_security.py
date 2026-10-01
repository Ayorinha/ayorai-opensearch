from ayorai_attractor.verification.response import VerificationResponse


def test_no_answer_response_is_safe() -> None:
    response = VerificationResponse.no_answer(
        "The corpus has no evidence for the requested attribute."
    )
    assert response.status.value == "no_answer"


def test_out_of_scope_response_is_safe() -> None:
    response = VerificationResponse.out_of_scope(
        "The question is outside the factual corpus scope."
    )
    assert response.status.value == "out_of_scope"
