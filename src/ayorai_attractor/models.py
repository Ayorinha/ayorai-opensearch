from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, WithJsonSchema


class QualityMode(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class FailureType(StrEnum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    EMPTY_RESPONSE = "empty_response"
    LOW_CONFIDENCE = "low_confidence"
    NO_SOURCES = "no_sources"
    WEAK_SOURCES = "weak_sources"
    CONTRADICTORY_RESULT = "contradictory_result"
    TOOL_FAILURE = "tool_failure"
    INVALID_FORMAT = "invalid_format"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    STALE_INFORMATION = "stale_information"
    UNSUPPORTED_CLAIM = "unsupported_claim"


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=10000)
    mode: QualityMode = QualityMode.BALANCED
    max_agents: int = Field(
        default=5,
        ge=1,
        le=100,
        description=(
            "Preferred form: JSON integer. Legacy coercion is preserved for "
            'compatibility: numeric strings (e.g. "5"), integral floats and '
            "booleans are still accepted for backward compatibility; removal "
            "is not scheduled before v0.6.0."
        ),
    )

    require_primary_source: Annotated[
        bool,
        WithJsonSchema(
            {
                "anyOf": [
                    {"type": "boolean"},
                    {"type": "integer", "enum": [0, 1]},
                ]
            }
        ),
    ] = Field(default=False)


class Evidence(BaseModel):
    id: str
    claim: str
    source: str
    excerpt: str
    independent: bool = True
    verified: bool = False


class Failure(BaseModel):
    type: FailureType
    message: str
    recoverable: bool = True


class AgentResult(BaseModel):
    agent: str
    output: str
    evidence_ids: list[str] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    mode: QualityMode
    answer: str
    verification: None = None
    verdict_authority: Literal["not_adjudicated"] = "not_adjudicated"
    formal_verification_endpoint: str = "/v1/verify"
    operation_status: Literal["completed", "failed", "not_recorded"] = "completed"
    confidence: float | None = Field(default=None, ge=0, le=1)
    notice: str = (
        "No factual verdict was adjudicated. Submit structured claims and evidence "
        "to /v1/verify for formal verification."
    )
    evidence: list[Evidence] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)
    agents_used: list[str] = Field(default_factory=list)
    trace_id: str


class AuditFindingResponse(BaseModel):
    code: str
    severity: str
    message: str


class AuditResponse(BaseModel):
    trace_id: str
    verification: None = None
    verdict_authority: Literal["not_adjudicated"] = "not_adjudicated"
    formal_verification_endpoint: str = "/v1/verify"
    operation_status: Literal["completed", "failed", "not_recorded"] = "completed"
    evidence_count: int = Field(ge=0)
    independent_evidence_count: int = Field(ge=0)
    verified_evidence_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    findings: list[AuditFindingResponse] = Field(default_factory=list)


class AuditTraceResponse(BaseModel):
    trace_id: str
    verification: None = None
    verdict_authority: Literal["not_adjudicated"] = "not_adjudicated"
    formal_verification_endpoint: str = "/v1/verify"
    operation_status: Literal["completed", "failed", "not_recorded"] = "completed"
    evidence_count: int = Field(ge=0)
    independent_evidence_count: int = Field(ge=0)
    verified_evidence_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)
    replay_digest: str
    legacy_verification: str | None = None
    replay_version: Literal["r2-v1", "r2-v2"]
    replay_integrity: Literal["valid", "invalid"]
