"""HTTP contract for POST /v1/check (claims or an answer checked against documents)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class CheckDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}$", description="Caller-chosen document id.")
    text: str = Field(min_length=1, max_length=200_000, description="Full document text.")
    source: str | None = Field(
        default=None, max_length=512, description="Human-readable origin (file name, title)."
    )
    url: HttpUrl | None = None


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["c1"] = "c1"
    documents: list[CheckDocument] = Field(min_length=1, max_length=20)
    claims: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Claims to check, verbatim. Provide either claims or answer.",
    )
    answer: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
        description="An AI answer to decompose into claims. Provide either claims or answer.",
    )

    @model_validator(mode="after")
    def _exactly_one_input(self) -> CheckRequest:
        if (self.claims is None) == (self.answer is None):
            raise ValueError("provide exactly one of 'claims' or 'answer'")
        if self.claims is not None and any(
            not item.strip() or len(item) > 2_000 for item in self.claims
        ):
            raise ValueError("each claim must be non-empty and at most 2000 characters")
        if len({doc.id for doc in self.documents}) != len(self.documents):
            raise ValueError("document ids must be unique")
        return self


class CheckEvidence(BaseModel):
    document_id: str
    start: int = Field(ge=0, description="Inclusive character offset in the document.")
    end: int = Field(ge=0, description="Exclusive character offset in the document.")
    excerpt: str
    stance: Literal["supports", "contradicts", "neutral"]


class CheckClaimResult(BaseModel):
    claim_id: str
    claim: str
    status: str = Field(description="Judge verdict, or an abstention policy.")
    verdict: str | None = Field(description="Judge verdict; null when the system abstains.")
    confidence: float = Field(ge=0, le=1)
    evidence: list[CheckEvidence]
    rationale: str
    abstention_reason: str | None = None


class CheckDocumentDigest(BaseModel):
    id: str
    sha256: str
    characters: int = Field(ge=0)


class CheckResponse(BaseModel):
    schema_version: Literal["c1"] = "c1"
    trace_id: str
    engine: dict[str, str]
    documents: list[CheckDocumentDigest]
    results: list[CheckClaimResult]
    summary: dict[str, int]
    scope_note: str = (
        "Closed-world check against the supplied documents only. Under the ADR-002 Judge, "
        "'partially_supported' means support from a single independent source and 'verified' "
        "support from two or more independent documents. An abstention means "
        "the documents do not establish the claim; it is not a statement that the claim is false."
    )
