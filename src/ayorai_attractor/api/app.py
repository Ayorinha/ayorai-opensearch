import hashlib
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ayorai_attractor import __version__
from ayorai_attractor.api.auth import (
    PRINCIPAL_STATE_KEY,
    TENANT_PRINCIPALS_STATE_KEY,
    TENANT_STATE_KEY,
    APIKeyAuthMiddleware,
    validate_auth_configuration,
)
from ayorai_attractor.api.http_metrics import http_metrics
from ayorai_attractor.api.keys import DEFAULT_TENANT
from ayorai_attractor.api.load_control import (
    HeavyRouteConcurrencyLimitMiddleware,
    inflight_scope_from_env,
    max_inflight_from_env,
)
from ayorai_attractor.api.logging_config import configure_logging
from ayorai_attractor.api.verify_log import (
    close_verify_log,
    get_verify_log,
    validate_verify_log_configuration,
    verify_log_mode,
)
from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.auditlog.store import (
    IdempotencyConflict,
    VerificationEvent,
    valid_idempotency_key,
)
from ayorai_attractor.models import (
    AuditFindingResponse,
    AuditResponse,
    AuditTraceResponse,
    QualityMode,
    SearchRequest,
    SearchResponse,
)
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.factory import validate_provider_configuration
from ayorai_attractor.verification.api_models import (
    ClaimJudgmentResponse,
    Judge2VerificationRequest,
    Judge2VerificationResponse,
    Traceability,
    VerificationAPIResponse,
    VerificationRequest,
)
from ayorai_attractor.verification.check_models import (
    AuditV2Request,
    AuditV2Response,
    CheckDocument,
    CheckRequest,
    CheckResponse,
    FieldsRequest,
    FieldsResponse,
    adjudication_sha256,
)
from ayorai_attractor.verification.document_check import CheckDocumentInput, check_documents
from ayorai_attractor.verification.document_ingest import (
    DocumentIngestError,
    IngestedDocument,
    ingest,
)
from ayorai_attractor.verification.extraction import RuleClaimExtractor
from ayorai_attractor.verification.field_check import (
    FIELD_CHECK_VERSION,
    FieldSpec,
    check_fields,
)
from ayorai_attractor.verification.judge import InvalidJudgeInput, judge
from ayorai_attractor.verification.judge2 import adjudicate
from ayorai_attractor.verification.judge2.explanations import explain_canonical_result
from ayorai_attractor.verification.models import Evidence, Verdict
from ayorai_attractor.verification.response import ResponsePolicy

logger = logging.getLogger(__name__)

engine = Attractor()
audit_store = AuditTraceStore()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release persistent resources when the API process shuts down."""
    validate_auth_configuration()
    # Fail closed like authentication: a provider configuration that every
    # request would reject must not start a partially configured service.
    validate_provider_configuration()
    max_inflight_from_env()
    inflight_scope_from_env()
    validate_verify_log_configuration()
    configure_logging()
    try:
        yield
    finally:
        audit_store.close()
        close_verify_log()


# Malformed JSON is reported as 422 (type json_invalid), never 400.
_HTTP_401_RESPONSE: dict[str, Any] = {
    "description": "Missing or invalid API key (ATTRACTOR_AUTH_MODE=api_key).",
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
_HTTP_413_RESPONSE: dict[str, Any] = {
    "description": "Request body exceeds the configured size limit.",
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

_HTTP_429_RESPONSE: dict[str, Any] = {
    "description": "The request rate limit was exceeded.",
    "headers": {
        "Retry-After": {
            "description": "Seconds to wait before retrying the request.",
            "schema": {"type": "integer", "minimum": 1},
        }
    },
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


_HTTP_503_RESPONSE: dict[str, Any] = {
    "description": "Too many verification requests in flight on this worker; retry later.",
    "headers": {
        "Retry-After": {
            "description": "Seconds to wait before retrying the request.",
            "schema": {"type": "integer", "minimum": 1},
        }
    },
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
# Between authentication and body buffering: unauthenticated requests never take
# a slot, and a rejected request is answered before its body is read.
app.add_middleware(HeavyRouteConcurrencyLimitMiddleware)
app.add_middleware(APIKeyAuthMiddleware)


@app.exception_handler(StarletteHTTPException)
async def _body_encoding_as_json_invalid(request: Request, exc: StarletteHTTPException) -> Response:
    """Answer a body that is not valid UTF-8 like any other malformed JSON (422).

    FastAPI parses JSON bodies with ``json.loads(bytes)``. Invalid UTF-8 raises
    UnicodeDecodeError rather than JSONDecodeError, which FastAPI turns into a
    generic 400. JSON text must be UTF-8 (RFC 8259, section 8.1), so this is a
    JSON decode error and gets the same documented 422 ``json_invalid`` envelope.
    Every other HTTPException keeps FastAPI's default handling.
    """
    cause = exc.__cause__
    if exc.status_code == 400 and isinstance(cause, UnicodeDecodeError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "type": "json_invalid",
                        "loc": ["body", cause.start],
                        "msg": "JSON decode error",
                        "input": {},
                        "ctx": {"error": "Request body is not valid UTF-8"},
                    }
                ]
            },
        )
    return await http_exception_handler(request, exc)


def _principal(http_request: Request) -> str | None:
    """Principal set by APIKeyAuthMiddleware; None when authentication is off."""
    value = getattr(http_request.state, PRINCIPAL_STATE_KEY, None)
    return value if isinstance(value, str) else None


def _tenant_principals(http_request: Request) -> frozenset[str] | None:
    """Principals of the requester's tenant (ADR-013), set by APIKeyAuthMiddleware."""
    value = getattr(http_request.state, TENANT_PRINCIPALS_STATE_KEY, None)
    return value if isinstance(value, frozenset) else None


def _tenant(http_request: Request) -> str:
    value = getattr(http_request.state, TENANT_STATE_KEY, None)
    return value if isinstance(value, str) else DEFAULT_TENANT


# Liveness: the process answers. It does not check dependencies (see /ready). The
# docstring is left out on purpose: it would change the published OpenAPI contract.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ayorai-attractor"}


@app.get("/ready", include_in_schema=False)
def ready() -> Response:
    """Readiness: the audit store answers. Unauthenticated, like /health; no details."""
    if audit_store.ping():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "not_ready"}, status_code=503)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus text exposition; protected by the API key like every other route."""
    return Response(http_metrics.render(), media_type="text/plain; version=0.0.4")


def _record_verification(
    canonical_result: dict[str, Any], http_request: Request, mode: str
) -> dict[str, Any]:
    """Record one r2-a decision (ADR-010 phase 3); fail closed in required mode."""
    key = http_request.headers.get("idempotency-key")
    if key is not None and not valid_idempotency_key(key):
        raise HTTPException(
            status_code=422, detail="Idempotency-Key must be 1-128 visible ASCII characters"
        )
    event = VerificationEvent(
        input_sha256=str(canonical_result["input_sha256"]),
        output_sha256=str(canonical_result["output_sha256"]),
        rules_sha256=str(canonical_result["rules_sha256"]),
        decision_state=str(canonical_result["decision_state"]),
        verdict=(
            str(canonical_result["verdict"])
            if canonical_result.get("verdict") is not None
            else None
        ),
        client=_principal(http_request) or "anonymous",
        tenant=_tenant(http_request),
        received_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        software_id=f"ayorai-opensearch/{__version__}",
    )
    try:
        receipt = get_verify_log().append(event, key)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        http_metrics.audit_record_failed()
        # Only the exception type: the message may carry request-derived data.
        logger.error("verification log append failed (mode=%s): %s", mode, type(exc).__name__)
        if mode == "required":
            # Owner decision 3: no verdict circulates unrecorded.
            raise HTTPException(
                status_code=503, detail="Verification not recorded; retry with the same key."
            ) from exc
        return {"audit_status": "not_recorded"}
    return {"audit_status": "recorded", "audit_receipt": receipt}


@app.get("/v1/verify/log", include_in_schema=False)
def verify_log_state() -> Response:
    """Latest signed checkpoint and verifier key, for offline receipt verification."""
    if verify_log_mode() == "off":
        return JSONResponse({"detail": "Verification log is off"}, status_code=404)
    log = get_verify_log()
    return JSONResponse(
        {
            "origin": log.origin,
            "verifier_key": log.verifier_key,
            "checkpoint": log.latest_checkpoint(),
        }
    )


def _record_trace(
    response: SearchResponse,
    report: AuditReport,
    owner: str | None,
    adjudication: tuple[str | None, str] | None = None,
) -> None:
    """Record an audit trace and count the failures for alerting (re-raised)."""
    try:
        audit_store.record(response, report, owner=owner, adjudication=adjudication)
    except Exception:
        http_metrics.audit_record_failed()
        raise


@app.post(
    "/v1/opensearch",
    response_model=SearchResponse,
    responses={
        401: _HTTP_401_RESPONSE,
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def opensearch(request: SearchRequest) -> SearchResponse:
    return engine.run(request)


@app.post(
    "/v1/audit",
    response_model=AuditResponse,
    responses={
        401: _HTTP_401_RESPONSE,
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def audit(request: SearchRequest, http_request: Request) -> AuditResponse:
    """Run the engine and expose a deterministic audit of its evidence."""
    response = engine.run(request)
    report = AuditReport.from_response(response)
    _record_trace(response, report, _principal(http_request))
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
                stage=item.stage,
            )
            for item in report.findings
        ],
    )


def _ingest_or_422(doc: CheckDocument, loc: list[Any]) -> IngestedDocument:
    try:
        return ingest(text=doc.text, content_base64=doc.content_base64, media_type=doc.media_type)
    except DocumentIngestError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"type": "document_ingest_error", "loc": loc, "msg": str(exc)}],
        ) from exc


@app.post(
    "/v1/check",
    response_model=CheckResponse,
    responses={
        401: _HTTP_401_RESPONSE,
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def check(request: CheckRequest) -> CheckResponse:
    """Check claims, or an AI answer, against the supplied documents.

    Closed world and deterministic: relevant passages are selected from the documents,
    a conservative stance detector labels them and the ADR-002 Judge decides. Each
    piece of evidence carries exact character offsets; the response carries the SHA-256
    of every document and the version of every component.
    """
    inputs = []
    for position, doc in enumerate(request.documents):
        ingested = _ingest_or_422(doc, ["body", "documents", position])
        inputs.append(
            CheckDocumentInput(
                id=doc.id,
                text=ingested.text,
                source=doc.source,
                url=str(doc.url) if doc.url is not None else None,
                media_type=ingested.media_type,
                page_starts=ingested.page_starts,
                source_sha256=ingested.source_sha256,
            )
        )
    result = check_documents(
        inputs,
        claims=request.claims,
        answer=request.answer,
    )
    return CheckResponse.model_validate(
        {
            "trace_id": result.trace_id,
            "engine": result.engine,
            "documents": list(result.documents),
            "results": [
                {
                    "claim_id": item.claim_id,
                    "claim": item.claim,
                    "status": item.status,
                    "verdict": item.verdict,
                    "confidence": item.confidence,
                    "evidence": [vars(view) for view in item.evidence],
                    "rationale": item.rationale,
                    "abstention_reason": item.abstention_reason,
                }
                for item in result.results
            ],
            "summary": result.summary,
        }
    )


def _independent_documents(response: SearchResponse) -> list[CheckDocumentInput]:
    """Independent retrieved sources become documents; model output never does."""
    seen: set[str] = set()
    documents: list[CheckDocumentInput] = []
    for item in response.evidence:
        text = item.excerpt.strip()
        if not item.independent or not text or text in seen:
            continue
        seen.add(text)
        url = item.source if item.source.startswith(("https://", "http://")) else None
        documents.append(
            CheckDocumentInput(
                id=f"src_{len(documents) + 1:03d}",
                text=text,
                source=item.source[:512] or None,
                # The source URL is the canonical URL: two hits from the same URL are
                # one cluster for the Judge, never two independent sources.
                url=url if url is not None and len(url) <= 2048 else None,
                retrieved_by_server=True,
            )
        )
    return documents


@app.post(
    "/v2/audit",
    response_model=AuditV2Response,
    responses={
        401: _HTTP_401_RESPONSE,
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def audit_v2(request: AuditV2Request, http_request: Request) -> AuditV2Response:
    """Search, then adjudicate claims against the independent sources found (end to end).

    The engine answers the query and retrieves sources. Only independent sources are
    checked against; the claims are the caller's, the caller's answer decomposed, or
    by default the engine's own answer decomposed. Each claim goes through the same
    passage selection, stance detection and ADR-002 Judge as /v1/check. The run is
    then recorded as an r2-v4 audit trace owned by the calling key, binding the
    claim-check digest and ``adjudication_sha256`` of the returned adjudication.
    """
    response = engine.run(SearchRequest(query=request.query, mode=QualityMode(request.mode)))
    report = AuditReport.from_response(response)

    if request.claims is not None:
        claims_source, claims, answer = "caller_claims", list(request.claims), None
    elif request.answer is not None:
        claims_source, claims, answer = "caller_answer", None, request.answer
    elif response.operation_status == "completed" and response.answer.strip():
        claims_source, claims, answer = "engine_answer", None, response.answer
    else:
        claims_source, claims, answer = "none", None, None

    documents = _independent_documents(response)
    check_trace_id: str | None = None
    engine_info: dict[str, str] = {"judge": "ADR-002"}
    digests: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    if claims_source != "none" and documents:
        result = check_documents(documents, claims=claims, answer=answer)
        check_trace_id, engine_info, digests = (
            result.trace_id,
            dict(result.engine),
            list(result.documents),
        )
        results = [
            {
                "claim_id": item.claim_id,
                "claim": item.claim,
                "status": item.status,
                "verdict": item.verdict,
                "confidence": item.confidence,
                "evidence": [vars(view) for view in item.evidence],
                "rationale": item.rationale,
                "abstention_reason": item.abstention_reason,
            }
            for item in result.results
        ]
    elif claims_source != "none":
        texts = (
            claims
            if claims is not None
            else [item.claim.text for item in RuleClaimExtractor().extract(answer or "").claims]
        )
        results = [
            {
                "claim_id": f"clm_{index:03d}",
                "claim": text,
                "status": ResponsePolicy.ABSTAIN_NO_ANSWER.value,
                "verdict": None,
                "confidence": 1.0,
                "evidence": [],
                "rationale": "No independent source was retrieved for the query.",
                "abstention_reason": "no_independent_source",
            }
            for index, text in enumerate(texts, start=1)
        ]
    summary: dict[str, int] = {}
    for item in results:
        key = item["verdict"] or item["status"]
        summary[key] = summary.get(key, 0) + 1
    placeholder = "0" * 64
    body = AuditV2Response.model_validate(
        {
            "trace_id": report.trace_id,
            "adjudication_sha256": placeholder,
            "check_trace_id": check_trace_id,
            "operation_status": response.operation_status,
            "claims_source": claims_source,
            "answer": response.answer,
            "engine": engine_info,
            "documents": digests,
            "results": results,
            "summary": dict(sorted(summary.items())),
            "failure_count": report.failure_count,
        }
    )
    # The digest is taken over the serialized body the client receives, then bound to
    # the trace: the trace is recorded only after adjudication, so it attests the
    # verdicts actually returned (r2-v4), not just the retrieval counts.
    digest = adjudication_sha256(body.model_dump(mode="json"))
    _record_trace(response, report, _principal(http_request), (check_trace_id, digest))
    return body.model_copy(update={"adjudication_sha256": digest})


@app.post(
    "/v1/fields",
    response_model=FieldsResponse,
    responses={
        401: _HTTP_401_RESPONSE,
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def fields(request: FieldsRequest) -> FieldsResponse:
    """Compare submitted field values (amount, date, CPF/CNPJ, names) with a document.

    Deterministic: each field is located next to its labels and normalised by type;
    the outcome is conforme, divergente (with the document's value and excerpt),
    ausente (abstention) or invalido (malformed expected value).
    """
    ingested = _ingest_or_422(request.document, ["body", "document"])
    specs = [
        FieldSpec(item.name, item.type, item.value, tuple(item.labels)) for item in request.fields
    ]
    results = check_fields(ingested.text, specs)
    text_sha = hashlib.sha256(ingested.text.encode("utf-8")).hexdigest()
    engine = {
        "field_check": FIELD_CHECK_VERSION,
        "trace": "fields-trace-2",
    }
    trace_payload = json.dumps(
        {
            "engine": engine,
            "document": {
                "id": request.document.id,
                "media_type": ingested.media_type,
                "sha256": text_sha,
                "source_sha256": ingested.source_sha256,
                "page_starts": list(ingested.page_starts),
            },
            "fields": [[s.name, s.type, s.value, list(s.labels)] for s in specs],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    summary = {
        outcome: 0 for outcome in ("conforme", "divergente", "ambiguo", "ausente", "invalido")
    }
    for item in results:
        summary[item.outcome] += 1
    return FieldsResponse.model_validate(
        {
            "trace_id": "fld_" + hashlib.sha256(trace_payload.encode("utf-8")).hexdigest()[:32],
            "engine": engine,
            "document": {
                "id": request.document.id,
                "sha256": text_sha,
                "characters": len(ingested.text),
                "media_type": ingested.media_type,
                "pages": len(ingested.page_starts),
                "source_sha256": ingested.source_sha256,
            },
            "results": [
                dict(
                    vars(item),
                    page=ingested.page_of(item.start) if item.start is not None else None,
                )
                for item in results
            ],
            "summary": summary,
        }
    )


_VERIFY_REQUEST_BODY: dict[str, Any] = {
    "parameters": [
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": False,
            "description": (
                "r2-a with the verification log on (ADR-009 §15.1): same key and same input "
                "return the same event and receipt; same key with another input is a 409. "
                "With the log on, the key must be 1-128 visible ASCII characters (else 422); "
                "with the log off, or for r1-a, the header is ignored."
            ),
            "schema": {"type": "string"},
        }
    ],
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
    },
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
        401: _HTTP_401_RESPONSE,
        409: {
            "description": "Idempotency-Key already used for a different input (verify log on).",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                        "required": ["detail"],
                    }
                }
            },
        },
        413: _HTTP_413_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
        503: _HTTP_503_RESPONSE,
    },
)
def verify(payload: Annotated[Any, Body()], http_request: Request) -> Any:
    """Dispatch r1-a unchanged or expose the canonical Judge 2.0.0 result for r2-a."""
    if payload is None:
        # Preserve the frozen r1-a HTTP 422 body for a JSON null request.
        raise RequestValidationError(
            [
                {
                    "type": "missing",
                    "loc": ("body",),
                    "msg": "Field required",
                    "input": None,
                }
            ],
            body=payload,
        )
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
        content = response.model_dump(mode="json", exclude={"audit_status", "audit_receipt"})
        mode = verify_log_mode()
        if mode != "off":
            content.update(_record_verification(canonical_result, http_request, mode))
        return JSONResponse(content=content)

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
    responses={
        401: _HTTP_401_RESPONSE,
        404: _HTTP_404_RESPONSE,
        422: _HTTP_422_RESPONSE,
        429: _HTTP_429_RESPONSE,
    },
)
def audit_trace(trace_id: str, http_request: Request) -> AuditTraceResponse:
    """Return persisted audit metadata without exposing raw evidence or prompts."""
    saved = audit_store.get(
        trace_id,
        requester=_principal(http_request),
        tenant_principals=_tenant_principals(http_request),
    )
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
