"""Strict API contracts for the R1-a deterministic verification surface."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import Claim, Evidence, StanceEdge, Verdict
from .response import ResponsePolicy


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
    status: Verdict | ResponsePolicy
    verdict: Verdict | None = None
    judgments: list[ClaimJudgmentResponse]
    traceability: Traceability


class Judge2VerificationRequest(BaseModel):
    """Strict JSON contract for the r2-a Judge 2.0.0 API path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["r2-a"]
    protocol_version: Literal["r2-a"] = "r2-a"
    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    atoms: list[dict[str, object]]
    evidence: list[Evidence] = Field(default_factory=list)
    stances: list[dict[str, object]] = Field(default_factory=list)
    source_texts: dict[str, str]
    out_of_scope: bool = False
    factual_claim: bool = True
    temporal_anchor_present: bool = True
    retrieval_succeeded: bool = True
    evidence_pool_integrity_ok: bool = True
