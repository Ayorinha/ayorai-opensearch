import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import (
    AuditFindingResponse,
    AuditResponse,
    AuditTraceResponse,
    SearchRequest,
    SearchResponse,
)
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.verification.api_models import (
    ClaimJudgmentResponse,
    Judge2VerificationRequest,
    Traceability,
    VerificationAPIResponse,
    VerificationRequest,
)
from ayorai_attractor.verification.judge import InvalidJudgeInput, judge
from ayorai_attractor.verification.judge2 import adjudicate
from ayorai_attractor.verification.models import Verdict
from ayorai_attractor.verification.response import ResponsePolicy

engine = Attractor()
audit_store = AuditTraceStore()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release persistent resources when the API process shuts down."""
    try:
        yield
    finally:
        audit_store.close()


app = FastAPI(
    title="AYORAI ATTRACTOR",
    version="0.1.0",
    description="Adaptive multi-agent intelligence and verification engine.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ayorai-attractor"}


@app.post("/v1/opensearch", response_model=SearchResponse)
def opensearch(request: SearchRequest) -> SearchResponse:
    return engine.run(request)


@app.post("/v1/audit", response_model=AuditResponse)
def audit(request: SearchRequest) -> AuditResponse:
    """Run the engine and expose a deterministic audit of its evidence."""
    response = engine.run(request)
    report = AuditReport.from_response(response)
    audit_store.record(response, report)
    return AuditResponse(
        trace_id=report.trace_id,
        verification=None,
        verdict_authority="not_adjudicated",
        formal_verification_endpoint="/v1/verify",
        operation_status=response.operation_status,
        evidence_count=report.evidence_count,
        independent_evidence_count=report.independent_evidence_count,
        verified_evidence_count=report.verified_evidence_count,
        failure_count=report.failure_count,
        findings=[
            AuditFindingResponse(
                code=item.code,
                severity=item.severity.value,
                message=item.message,
            )
            for item in report.findings
        ],
    )


_VERIFY_REQUEST_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/VerificationRequest"},
                        {"$ref": "#/components/schemas/Judge2VerificationRequest"},
                    ]
                }
            }
        },
    }
}


@app.post(
    "/v1/verify",
    response_model=VerificationAPIResponse,
    openapi_extra=_VERIFY_REQUEST_BODY,
)
def verify(payload: Annotated[Any, Body()]) -> Any:
    """Dispatch r1-a unchanged or expose the canonical Judge 2.0.0 result for r2-a."""
    version = payload.get("schema_version", "r1-a") if isinstance(payload, dict) else "r1-a"

    if version == "r2-a":
        try:
            request2 = Judge2VerificationRequest.model_validate_json(
                json.dumps(payload, ensure_ascii=False)
            )
        except ValidationError as exc:
            errors = [
                {
                    **{key: value for key, value in error.items() if key != "url"},
                    "loc": ("body", *error["loc"]),
                }
                for error in exc.errors()
            ]
            raise RequestValidationError(errors, body=payload) from exc

        result = adjudicate({
            "protocol_version": request2.protocol_version,
            "claim_id": request2.claim_id,
            "claim_text": request2.claim_text,
            "atoms": request2.atoms,
            "evidence": request2.evidence,
            "stances": request2.stances,
            "source_texts": request2.source_texts,
            "out_of_scope": request2.out_of_scope,
            "factual_claim": request2.factual_claim,
            "temporal_anchor_present": request2.temporal_anchor_present,
            "retrieval_succeeded": request2.retrieval_succeeded,
            "evidence_pool_integrity_ok": request2.evidence_pool_integrity_ok,
        })
        response_policy = None
        if result.decision_state == "ABSTAINED":
            response_policy = (
                ResponsePolicy.ABSTAIN_OUT_OF_SCOPE.value
                if "OUT_OF_SCOPE" in result.reason_codes
                else ResponsePolicy.ABSTAIN_NO_ANSWER.value
            )
        return JSONResponse(
            content={
                "schema_version": "r2-a",
                "result": result.to_dict(),
                "response_policy": response_policy,
            }
        )

    try:
        request = VerificationRequest.model_validate(payload, from_attributes=True)
    except ValidationError as exc:
        errors = [
            {
                **{key: value for key, value in error.items() if key != "url"},
                "loc": ("body", *error["loc"]),
            }
            for error in exc.errors()
        ]
        raise RequestValidationError(errors, body=payload) from exc

    if not request.claims:
        return VerificationAPIResponse(
            status=ResponsePolicy.ABSTAIN_OUT_OF_SCOPE,
            verdict=None,
            judgments=[],
            traceability=Traceability(adr="ADR-002", rules=["§5"]),
        )

    try:
        judgments, verdict = judge(request.claims, request.evidence, request.stances)
    except InvalidJudgeInput as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": exc.code,
                    "loc": ["body", exc.field],
                    "msg": str(exc),
                }
            ],
        ) from exc
    status = (
        ResponsePolicy.ABSTAIN_NO_ANSWER
        if verdict is Verdict.UNVERIFIED
        else verdict
    )
    api_verdict = None if status is ResponsePolicy.ABSTAIN_NO_ANSWER else verdict
    return VerificationAPIResponse(
        status=status,
        verdict=api_verdict,
        judgments=[
            ClaimJudgmentResponse(
                claim_id=item.claim_id,
                support_clusters=item.support_clusters,
                contradiction_clusters=item.contradiction_clusters,
                provenance_complete=item.provenance_complete,
                verdict=item.verdict,
            )
            for item in judgments
        ],
        traceability=Traceability(
            adr="ADR-002",
            rules=["§1", "§2", "§3", "§4", "§5", "§9"],
        ),
    )


@app.get("/v1/audit/{trace_id}", response_model=AuditTraceResponse)
def audit_trace(trace_id: str) -> AuditTraceResponse:
    """Return persisted audit metadata without exposing raw evidence or prompts."""
    saved = audit_store.get(trace_id)
    if saved is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="audit trace not found")
    return saved



def _verify_contracts_schema_only(
    body: Annotated[VerificationRequest | Judge2VerificationRequest, Body()],
) -> None:  # pragma: no cover - documentation-only signature, never routed
    """Expose both /v1/verify request contracts to OpenAPI generation."""


def _openapi_with_verify_schemas() -> dict[str, Any]:
    """Generate OpenAPI with FastAPI's own component names for both contracts."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    from fastapi.routing import APIRoute

    phantom_path = "/__verify_contracts__"
    phantom = APIRoute(phantom_path, _verify_contracts_schema_only, methods=["POST"])
    schema = get_openapi(
        title=app.title, version=app.version, routes=[*app.routes, phantom]
    )
    schema["paths"].pop(phantom_path, None)
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_verify_schemas  # type: ignore[method-assign]
