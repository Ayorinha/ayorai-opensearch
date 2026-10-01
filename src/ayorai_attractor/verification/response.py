"""Response-status contracts for R1 no-answer and out-of-scope handling."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResponseStatus(StrEnum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    REFUTED = "refuted"
    UNVERIFIED = "unverified"
    ABSTAIN_NO_ANSWER = "abstain/no_answer"
    ABSTAIN_OUT_OF_SCOPE = "abstain/out_of_scope"


class VerificationResponse( BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: ResponseStatus
    verdict: ResponseStatus | None = None
    rationale: str = Field(min_length=1)

    @classmethod
    def no_answer(cls, rationale: str) -> "VerificationResponse":
        return cls(
            status=ResponseStatus.ABSTAIN_NO_ANSWER,
            verdict=None,
            rationale=rationale,
        )

    @classmethod
    def out_of_scope(cls, rationale: str) -> "VerificationResponse":
        return cls(
            status=ResponseStatus.ABSTAIN_OUT_OF_SCOPE,
            verdict=None,
            rationale=rationale,
        )
