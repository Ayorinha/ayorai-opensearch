"""HTTP contract for POST /v1/check (claims or an answer checked against documents)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

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


class FieldSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$", description="Field name, e.g. valor.")
    type: Literal["money", "date", "cpf_cnpj", "number", "text"]
    value: str = Field(min_length=1, max_length=500, description="Expected value, as submitted.")
    labels: list[str] = Field(
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
