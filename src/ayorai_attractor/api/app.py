import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ayorai_attractor.api.auth import APIKeyAuthMiddleware, validate_auth_configuration
from ayorai_attractor.api.logging_config import configure_logging
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
    Judge2VerificationResponse,
    Traceability,
    VerificationAPIResponse,
    VerificationRequest,
)
from ayorai_attractor.verification.judge import InvalidJudgeInput, judge
from ayorai_attractor.verification.judge2 import adjudicate
from ayorai_attractor.verification.judge2.explanations import explain_canonical_result
from ayorai_attractor.verification.models import Evidence, Verdict
from ayorai_attractor.verification.response import ResponsePolicy

engine = Attractor()
audit_store = AuditTraceStore()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release persistent resources when the API process shuts down."""
    validate_auth_configuration()
    configure_logging()
    try:
        yield
    finally:
        audit_store.close()


_HTTP_400_RESPONSE: dict[str, Any] = {
    "description": "Request body could not be parsed as JSON.",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
                "required": ["detail"],
            }
        }
    },
}
_HTTP_422_RESPONSE: dict[str, Any] = {
    "description": "Request validation failed.",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {"detail": {"type": "array", "items": {"type": "object"}}},
                "required": ["detail"],
            }
        }
    },
}
_HTTP_404_RESPONSE: dict[str, Any] = {
    "description": "The requested audit trace does not exist.",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {"detail": {"type": "string"}},
                "required": ["detail"],
            }
        }
    },
}


_DEFAULT_MAX_BODY_BYTES = 2 * 1024 * 1024


class RequestBodyLimitMiddleware:
    """Bound buffered HTTP request bodies before application-level parsing."""

    def __init__(self, app: ASGIApp, max_body_bytes: int | None = None) -> None:
        self.app = app
        if max_body_bytes is None:
            raw_limit = os.getenv("ATTRACTOR_MAX_BODY_BYTES", str(_DEFAULT_MAX_BODY_BYTES))
            try:
                max_body_bytes = int(raw_limit)
            except ValueError as exc:
                raise ValueError("ATTRACTOR_MAX_BODY_BYTES must be a positive integer") from exc
        if max_body_bytes <= 0:
            raise ValueError("ATTRACTOR_MAX_BODY_BYTES must be a positive integer")
        self.max_body_bytes = max_body_bytes

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={"detail": "Request body exceeds the configured size limit"},
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_content_length = headers.get(b"content-length")
        if raw_content_length is not None:
            try:
                content_length = int(raw_content_length)
            except ValueError:
                content_length = 0
            if content_length > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)


app = FastAPI(
    title="AYORAI ATTRACTOR",
    version="0.1.0",
    description="Adaptive multi-agent intelligence and verification engine.",
    lifespan=lifespan,
)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(APIKeyAuthMiddleware)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ayorai-attractor"}


@app.post(
    "/v1/opensearch",
    response_model=SearchResponse,
    responses={400: _HTTP_400_RESPONSE, 422: _HTTP_422_RESPONSE},
)
def opensearch(request: SearchRequest) -> SearchResponse:
    return engine.run(request)


@app.post(
    "/v1/audit",
    response_model=AuditResponse,
    responses={400: _HTTP_400_RESPONSE, 422: _HTTP_422_RESPONSE},
)
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
    response_model=None,
    openapi_extra=_VERIFY_REQUEST_BODY,
    responses={
        200: {
            "description": "r1-a or r2-a verification result.",
            "content": {
                "application/json": {
                    "schema": {
                        "oneOf": [
                            {"$ref": "#/components/schemas/VerificationAPIResponse"},
                            {"$ref": "#/components/schemas/Judge2VerificationResponse"},
                        ]
                    }
                }
            },
        },
        400: _HTTP_400_RESPONSE,
        422: _HTTP_422_RESPONSE,
    },
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

        evidence_items: list[Evidence | dict[str, object]] = []
        for item in request2.evidence:
            evidence_data = item.model_dump()
            if evidence_data["end_offset"] <= evidence_data["start_offset"] or (
                evidence_data["origin_id"] is None and evidence_data["canonical_url"] is None
            ):
                evidence_items.append(evidence_data)
            else:
                try:
                    evidence_items.append(
                        Evidence.model_validate(evidence_data, from_attributes=True)
                    )
                except ValidationError:
                    evidence_items.append(evidence_data)

        result = adjudicate(
            {
                "protocol_version": request2.protocol_version,
                "claim_id": request2.claim_id,
                "claim_text": request2.claim_text,
                "atoms": [item.model_dump() for item in request2.atoms],
                "evidence": evidence_items,
                "stances": [item.model_dump() for item in request2.stances],
                "source_texts": request2.source_texts,
                "out_of_scope": request2.out_of_scope,
                "factual_claim": request2.factual_claim,
                "temporal_anchor_present": request2.temporal_anchor_present,
                "retrieval_succeeded": request2.retrieval_succeeded,
                "evidence_pool_integrity_ok": request2.evidence_pool_integrity_ok,
            }
        )
        response_policy = None
        if result.decision_state == "ABSTAINED":
            response_policy = (
                ResponsePolicy.ABSTAIN_OUT_OF_SCOPE
                if "OUT_OF_SCOPE" in result.reason_codes
                else ResponsePolicy.ABSTAIN_NO_ANSWER
            )
        canonical_result = result.to_dict()
        explanation = explain_canonical_result(canonical_result)
        response = Judge2VerificationResponse(
            schema_version="r2-a",
            result=canonical_result,
            simple_explanation=explanation["simple_explanation"],
            technical_explanation=explanation["technical_explanation"],
            response_policy=response_policy,
        )
        return JSONResponse(content=response.model_dump(mode="json"))

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
    status = ResponsePolicy.ABSTAIN_NO_ANSWER if verdict is Verdict.UNVERIFIED else verdict
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


@app.get(
    "/v1/audit/{trace_id}",
    response_model=AuditTraceResponse,
    responses={404: _HTTP_404_RESPONSE, 422: _HTTP_422_RESPONSE},
)
def audit_trace(trace_id: str) -> AuditTraceResponse:
    """Return persisted audit metadata without exposing raw evidence or prompts."""
    saved = audit_store.get(trace_id)
    if saved is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="audit trace not found")
    return saved


def _verify_contracts_schema_only(
    body: Annotated[VerificationRequest | Judge2VerificationRequest, Body()],
) -> VerificationAPIResponse | Judge2VerificationResponse:  # pragma: no cover
    """Expose both /v1/verify request contracts to OpenAPI generation."""
    raise RuntimeError("documentation-only route must never be called")


def _openapi_with_verify_schemas() -> dict[str, Any]:
    """Generate OpenAPI with FastAPI's own component names for both contracts."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    from fastapi.routing import APIRoute

    phantom_path = "/__verify_contracts__"
    phantom = APIRoute(phantom_path, _verify_contracts_schema_only, methods=["POST"])
    schema = get_openapi(title=app.title, version=app.version, routes=[*app.routes, phantom])
    schema["paths"].pop(phantom_path, None)
    verification_schema = schema["components"]["schemas"].get("VerificationRequest")
    if isinstance(verification_schema, dict):
        verification_schema["not"] = {
            "type": "object",
            "properties": {
                "evidence": {"maxItems": 0},
                "stances": {"minItems": 1},
            },
            "required": ["stances"],
        }
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_verify_schemas  # type: ignore[method-assign]


# Install last so request IDs also cover authentication and body-limit rejections.
def _install_request_context_middleware() -> None:
    from ayorai_attractor.api.request_context import RequestContextMiddleware

    app.add_middleware(RequestContextMiddleware)


_install_request_context_middleware()
