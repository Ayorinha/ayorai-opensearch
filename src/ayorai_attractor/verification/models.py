from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Claim(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)

class Stance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"

class Evidence(StrictModel):
    id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    retrieved_at: datetime
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
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

    @model_validator(mode="after")
    def require_origin_or_canonical_url(self) -> "Evidence":
        if self.origin_id is None and self.canonical_url is None:
            raise ValueError("evidence requires origin_id or canonical_url")
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self

class StanceEdge(StrictModel):
    id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    stance: Stance

class Verdict(StrEnum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNVERIFIED = "unverified"
    REFUTED = "refuted"
    CONFLICTING = "conflicting"

INSUFFICIENT_EVIDENCE_TO_VERDICT: dict[str, Verdict] = {
    "insufficient_evidence": Verdict.UNVERIFIED,
}
