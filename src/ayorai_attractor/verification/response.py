from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .models import Verdict


class ResponsePolicy(StrEnum):
    """Transport-level abstention policy; never a factual verdict."""

    ABSTAIN_NO_ANSWER = "abstain/no_answer"
    ABSTAIN_OUT_OF_SCOPE = "abstain/out_of_scope"
    ABSTAIN_PROCESSING_ERROR = "abstain/processing_error"


# Deprecated compatibility name for callers that used the former mixed status enum.
ResponseStatus = Verdict | ResponsePolicy


class VerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Verdict | ResponsePolicy
    verdict: Verdict | None = None
    rationale: str = Field(min_length=1)

    @classmethod
    def no_answer(cls, rationale: str) -> "VerificationResponse":
        return cls(status=ResponsePolicy.ABSTAIN_NO_ANSWER, verdict=None, rationale=rationale)

    @classmethod
    def out_of_scope(cls, rationale: str) -> "VerificationResponse":
        return cls(status=ResponsePolicy.ABSTAIN_OUT_OF_SCOPE, verdict=None, rationale=rationale)

    @classmethod
    def processing_error(cls, rationale: str) -> "VerificationResponse":
        return cls(
            status=ResponsePolicy.ABSTAIN_PROCESSING_ERROR,
            verdict=None,
            rationale=rationale,
        )
