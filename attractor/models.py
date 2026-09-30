from enum import Enum

from pydantic import BaseModel, Field


class QualityMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNVERIFIED = "unverified"
    FAILED = "failed"


class FailureType(str, Enum):
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
    max_agents: int = Field(default=5, ge=1, le=100)
    require_primary_source: bool = False


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
    verification: VerificationStatus
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)
    agents_used: list[str] = Field(default_factory=list)
    trace_id: str
