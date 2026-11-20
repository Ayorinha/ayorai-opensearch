"""HTTP contract for POST /v1/check (claims or an answer checked against documents)."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Annotated, Any, Literal

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, UrlConstraints, model_validator


def _exactly_one(first: list[str], second: list[str]) -> dict[str, Any]:
    """JSON Schema for "exactly one of two non-null inputs" (documents the validator)."""

    def present(names: list[str]) -> dict[str, Any]:
        return {
            "required": names,
            "properties": {name: {"not": {"type": "null"}} for name in names},
        }

    return {
        "oneOf": [
            {**present(first), "not": present(second[:1])},
            {**present(second), "not": present(first[:1])},
        ]
    }


_DOCUMENT_SCHEMA = _exactly_one(["text"], ["content_base64", "media_type"])
# A text document may only declare text/plain (or nothing).
_DOCUMENT_SCHEMA["oneOf"][0]["properties"]["media_type"] = {"enum": ["text/plain", None]}

ClaimText = Annotated[str, Field(min_length=1, max_length=2_000, pattern=r"\S")]


class CheckDocument(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_DOCUMENT_SCHEMA,
    )

    id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}$", description="Caller-chosen document id.")
    text: str | None = Field(
        default=None,
        min_length=1,
        max_length=200_000,
        pattern=r"\S",
        description="Full document text. Provide either text or content_base64.",
    )
    content_base64: str | None = Field(
        default=None,
        min_length=1,
        max_length=7_000_000,
        description="Base64 file content (PDF with a text layer, or UTF-8 text).",
    )
    media_type: Literal["text/plain", "application/pdf"] | None = Field(
        default=None, description="Required with content_base64."
    )
    source: str | None = Field(
        default=None, max_length=512, description="Human-readable origin (file name, title)."
    )
    # Below the 2083-character HttpUrl limit so the normalised URL (which may gain a
    # trailing slash) still fits the internal evidence model.
    url: Annotated[HttpUrl, UrlConstraints(max_length=2048)] | None = None

    @model_validator(mode="after")
    def _exactly_one_content(self) -> CheckDocument:
        if (self.text is None) == (self.content_base64 is None):
            raise ValueError("provide exactly one of 'text' or 'content_base64'")
        if self.content_base64 is not None and self.media_type is None:
            raise ValueError("'media_type' is required with 'content_base64'")
        return self


class CheckRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra=_exactly_one(["claims"], ["answer"])
    )

    schema_version: Literal["c1"] = "c1"
    documents: list[CheckDocument] = Field(min_length=1, max_length=20)
    claims: list[ClaimText] | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Claims to check, verbatim. Provide either claims or answer.",
    )
    answer: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
        pattern=r"\S",
        description="An AI answer to decompose into claims. Provide either claims or answer.",
    )

    @model_validator(mode="after")
    def _exactly_one_input(self) -> CheckRequest:
        if (self.claims is None) == (self.answer is None):
            raise ValueError("provide exactly one of 'claims' or 'answer'")
        if len({doc.id for doc in self.documents}) != len(self.documents):
            raise ValueError("document ids must be unique")
        return self


class CheckEvidence(BaseModel):
    document_id: str
    start: int = Field(ge=0, description="Inclusive character offset in the document.")
    end: int = Field(ge=0, description="Exclusive character offset in the document.")
    excerpt: str
    stance: Literal["supports", "contradicts", "neutral"]
    page: int = Field(ge=1, description="1-based page of the evidence start.")


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
    sha256: str = Field(description="SHA-256 of the checked (extracted) text.")
    characters: int = Field(ge=0)
    media_type: str
    pages: int = Field(ge=1)
    source_sha256: str = Field(description="SHA-256 of the original uploaded bytes or text.")
    provenance: Literal["client_supplied", "server_retrieved"] = Field(
        default="client_supplied",
        description=(
            "client_supplied: sent by the caller; its url/source are unverified metadata. "
            "server_retrieved: fetched by this server (POST /v2/audit). Only "
            "server_retrieved documents with a URL have complete provenance (ADR-002 §2), "
            "which the Judge requires for 'verified'."
        ),
    )


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


NonBlankLabel = Annotated[str, Field(min_length=1, max_length=128, pattern=r"\S")]


class FieldSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$", description="Field name, e.g. valor.")
    type: Literal["money", "date", "cpf_cnpj", "number", "text"]
    value: str = Field(
        min_length=1,
        max_length=500,
        pattern=r"\S",
        description="Expected value, as submitted.",
    )
    labels: list[NonBlankLabel] = Field(
        default_factory=list,
        max_length=10,
        description="Labels that introduce the field in the document (e.g. 'Vencimento').",
    )


class FieldsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["f1"] = "f1"
    document: CheckDocument
    fields: list[FieldSpecModel] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _unique_names(self) -> FieldsRequest:
        if len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("field names must be unique")
        return self


class FieldResultModel(BaseModel):
    name: str
    type: str
    expected: str
    expected_normalized: str | None
    outcome: Literal["conforme", "divergente", "ambiguo", "ausente", "invalido"]
    found: str | None
    found_normalized: str | None
    start: int | None
    end: int | None
    page: int | None
    excerpt: str | None
    reason: str


class FieldsResponse(BaseModel):
    trace_id: str
    engine: dict[str, str]
    document: CheckDocumentDigest
    results: list[FieldResultModel]
    summary: dict[str, int]
    scope_note: str = (
        "Deterministic field comparison against the supplied document only. 'ausente' means "
        "the value was not located next to the field labels; it is an abstention, not a "
        "finding of error."
    )


class AuditV2Request(BaseModel):
    """POST /v2/audit: search, then check claims against the independent sources found."""

    # At most one of claims/answer: documented in the schema so clients and contract
    # tests see the same rule the validator enforces.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "not": {
                "required": ["claims", "answer"],
                "properties": {
                    "claims": {"not": {"type": "null"}},
                    "answer": {"not": {"type": "null"}},
                },
            }
        },
    )

    schema_version: Literal["a2"] = "a2"
    query: str = Field(min_length=3, max_length=10_000, pattern=r"\S")
    mode: Literal["fast", "balanced", "deep"] = "balanced"
    claims: list[ClaimText] | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description=(
            "Claims to check, verbatim. Optional: without claims or answer, the engine's "
            "own answer to the query is checked."
        ),
    )
    answer: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
        pattern=r"\S",
        description="An AI answer to decompose into claims and check. Optional.",
    )

    @model_validator(mode="after")
    def _at_most_one_input(self) -> AuditV2Request:
        if self.claims is not None and self.answer is not None:
            raise ValueError("provide at most one of 'claims' or 'answer'")
        return self


ADJUDICATION_DIGEST_FIELDS = ("check_trace_id", "claims_source", "engine", "documents", "results")


def adjudication_sha256(response: Mapping[str, Any]) -> str:
    """SHA-256 of the RFC 8785 (JCS) encoding of the adjudication part of a /v2/audit response.

    ``response`` is the JSON response body (or ``AuditV2Response.model_dump(mode="json")``).
    Only ADJUDICATION_DIGEST_FIELDS are covered, so a client can recompute the digest from
    the body it received and compare it with the one bound to the persisted audit trace.
    """
    covered = {name: response[name] for name in ADJUDICATION_DIGEST_FIELDS}
    return hashlib.sha256(rfc8785.dumps(covered)).hexdigest()


class AuditV2Response(BaseModel):
    schema_version: Literal["a2"] = "a2"
    trace_id: str = Field(description="Persisted audit trace; readable via GET /v1/audit/{id}.")
    adjudication_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "SHA-256 of the RFC 8785 encoding of {check_trace_id, claims_source, engine, "
            "documents, results} of this response. The persisted r2-v4 trace binds the same "
            "value under its replay digest and HMAC."
        ),
    )
    check_trace_id: str | None = Field(
        description="Digest of the claim check; null when no independent source was found."
    )
    operation_status: Literal["completed", "failed", "not_recorded"]
    verdict_authority: Literal["adr-002-judge"] = "adr-002-judge"
    claims_source: Literal["caller_claims", "caller_answer", "engine_answer", "none"]
    answer: str = Field(description="The engine's answer to the query.")
    engine: dict[str, str]
    documents: list[CheckDocumentDigest]
    results: list[CheckClaimResult]
    summary: dict[str, int]
    failure_count: int = Field(ge=0)
    scope_note: str = (
        "Claims are checked only against independent sources retrieved for this query; "
        "model-generated text is never used as evidence. Under the ADR-002 Judge, "
        "'partially_supported' means support from a single independent source and "
        "'verified' support from two or more. An abstention means the retrieved sources "
        "do not establish the claim; it is not a statement that the claim is false."
    )
