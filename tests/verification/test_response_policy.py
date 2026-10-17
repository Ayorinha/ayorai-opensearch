from ayorai_attractor.api.app import app
from ayorai_attractor.verification.response import ResponseStatus


def test_response_status_compatibility_enum_remains_usable() -> None:
    assert ResponseStatus.VERIFIED == "verified"
    assert ResponseStatus("abstain/no_answer") is ResponseStatus.ABSTAIN_NO_ANSWER


def test_openapi_status_accepts_verdicts_and_response_policies() -> None:
    schema = app.openapi()["components"]["schemas"]
    status = schema["VerificationAPIResponse"]["properties"]["status"]
    references = {item["$ref"].rsplit("/", 1)[-1] for item in status["anyOf"]}
    assert references == {"Verdict", "ResponsePolicy"}

    accepted_values = {value for name in references for value in schema[name]["enum"]}
    assert accepted_values == {
        "verified",
        "supported",
        "partially_supported",
        "conflicting",
        "refuted",
        "unverified",
        "abstain/no_answer",
        "abstain/out_of_scope",
        "abstain/processing_error",
    }
