"""Strict API contracts for the R1-a deterministic verification surface."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

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


class Judge2AtomRequest(BaseModel):
    """Strict public schema for a Judge 2 atom and its source-text span."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    start_offset: int = Field(ge=0, le=9007199254740991)
    end_offset: int = Field(
        gt=0,
        le=9007199254740991,
        description=(
            "Exclusive end offset in source text; must be within the "
            "RFC 8785 safe-integer range."
        ),
    )


class Judge2StanceRequest(BaseModel):
    """Strict public schema for an explicit atom/evidence stance edge."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    atom_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    stance: Literal[
        "SUPPORTS", "CONTRADICTS", "NEUTRAL",
        "supports", "contradicts", "neutral",
    ]


class Judge2EvidenceRequest(BaseModel):
    """Strict r2-a evidence shape; relational offsets are adjudicated by Judge 2."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    retrieved_at: datetime
    start_offset: int = Field(ge=0, le=9007199254740991)
    end_offset: int = Field(
        ge=0,
        le=9007199254740991,
        description=(
            "Must be greater than start_offset; the relational invariant "
            "is enforced by the API and Judge 2."
        ),
    )
    excerpt: str = Field(min_length=1)
    origin_id: str | None = Field(default=None, min_length=1)
    canonical_url: HttpUrl | None = None
    normalized_content_hash: str | None = Field(default=None, min_length=1)
    cited_origin_id: str | None = Field(default=None, min_length=1)
    provenance_complete: bool = True

    @field_validator("retrieved_at", mode="before")
    @classmethod
    def parse_rfc3339_timestamp(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("retrieved_at must be a valid RFC3339 timestamp") from exc
        return value

    @field_validator("canonical_url", mode="before")
    @classmethod
    def parse_http_url(cls, value: object) -> object:
        if isinstance(value, str):
            return HttpUrl(value)
        return value


class Judge2VerificationRequest(BaseModel):
    """Strict JSON contract for the r2-a Judge 2.0.0 API path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["r2-a"]
    protocol_version: Literal["r2-a"] = "r2-a"
    claim_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    atoms: list[Judge2AtomRequest]
    evidence: list[Judge2EvidenceRequest] = Field(default_factory=list)
    stances: list[Judge2StanceRequest] = Field(default_factory=list)
    source_texts: dict[str, str]
    out_of_scope: bool = False
    factual_claim: bool = True
    temporal_anchor_present: bool = True
    retrieval_succeeded: bool = True
    evidence_pool_integrity_ok: bool = True


class Judge2VerificationResponse(BaseModel):
    """Additive r2-a response with explanations derived from canonical output."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["r2-a"]
    result: dict[str, object]
    simple_explanation: list[str] = Field(min_length=1, max_length=5)
    technical_explanation: dict[str, object]
    response_policy: ResponsePolicy | None = None
