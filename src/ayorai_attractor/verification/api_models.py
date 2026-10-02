"""Strict API contracts for the R1-a deterministic verification surface."""

from typing import Literal

from pydantic import Field

from .models import Claim, Evidence, StanceEdge, Verdict
from .response import ResponseStatus
from pydantic import BaseModel, ConfigDict


class Traceability(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    adr: Literal["ADR-002"] = "ADR-002"
    rules: list[str] = Field(min_length=1)


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["r1-a"] = "r1-a"
    claims: list[Claim] = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    stances: list[StanceEdge] = Field(default_factory=list)


class ClaimJudgmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    claim_id: str
    support_clusters: int = Field(ge=0)
    contradiction_clusters: int = Field(ge=0)
    provenance_complete: bool
    verdict: Verdict


class VerificationAPIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["r1-a"] = "r1-a"
    status: ResponseStatus
    verdict: Verdict | None = None
    judgments: list[ClaimJudgmentResponse]
    traceability: Traceability
