import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from ayorai_attractor.api import app as api
from ayorai_attractor.api.app import RequestBodyLimitMiddleware
from ayorai_attractor.models import (
    Evidence,
    QualityMode,
    SearchResponse,
)


class FakeEngine:
    def run(self, request):  # type: ignore[no-untyped-def]
        return SearchResponse(
            query=request.query,
            mode=QualityMode.BALANCED,
            answer="test",
            verification=None,
            confidence=0.9,
            evidence=[
                Evidence(
                    id="e1",
                    claim="claim",
                    source="source-a",
                    excerpt="excerpt",
                    independent=True,
                    verified=True,
                ),
                Evidence(
                    id="e2",
                    claim="claim",
                    source="source-b",
                    excerpt="excerpt",
                    independent=True,
                    verified=False,
                ),
            ],
            failures=[],
            agents_used=["fake"],
            trace_id="tr_api",
        )


def test_audit_endpoint_returns_deterministic_report(monkeypatch, tmp_path, request) -> None:  # type: ignore[no-untyped-def]
    from ayorai_attractor.audit_store import AuditTraceStore

    monkeypatch.setattr(api, "engine", FakeEngine())
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(api, "audit_store", store)
    client = TestClient(api.app)

    response = client.post("/v1/audit", json={"query": "test query"})

    assert response.status_code == 200
    assert response.json() == {
        "trace_id": "tr_api",
        "verification": None,
        "verdict_authority": "not_adjudicated",
        "formal_verification_endpoint": "/v1/verify",
        "operation_status": "completed",
        "evidence_count": 2,
        "independent_evidence_count": 2,
        "verified_evidence_count": 1,
        "failure_count": 0,
        "findings": [],
    }


def test_audit_endpoint_rejects_short_query() -> None:
    client = TestClient(api.app)

    response = client.post("/v1/audit", json={"query": "no"})

    assert response.status_code == 422


def test_audit_trace_lookup_returns_persisted_metadata(monkeypatch, tmp_path, request) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(api, "engine", FakeEngine())
    from ayorai_attractor.audit_store import AuditTraceStore

    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(api, "audit_store", store)
    client = TestClient(api.app)

    response = client.post("/v1/audit", json={"query": "test query"})
    trace_id = response.json()["trace_id"]
    lookup = client.get(f"/v1/audit/{trace_id}")

    assert lookup.status_code == 200
    body = lookup.json()
    assert body["trace_id"] == "tr_api"
    assert body["verification"] is None
    assert body["verdict_authority"] == "not_adjudicated"
    assert body["formal_verification_endpoint"] == "/v1/verify"
    assert body["operation_status"] == "completed"
    assert body["replay_digest"]
    assert body["legacy_verification"] is None
    assert body["replay_version"] == "r2-v2"
    assert body["replay_integrity"] == "valid"
    assert body["evidence_count"] == 2


def test_audit_trace_lookup_returns_404_for_unknown_trace(monkeypatch, tmp_path, request) -> None:  # type: ignore[no-untyped-def]
    from ayorai_attractor.audit_store import AuditTraceStore

    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(api, "audit_store", store)
    client = TestClient(api.app)

    response = client.get("/v1/audit/missing")

    assert response.status_code == 404


@pytest.fixture(scope="module", autouse=True)
def close_original_global_audit_store():
    yield
    api.audit_store.close()


def test_api_lifespan_closes_audit_store(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    closed: list[bool] = []

    class CloseTracker:
        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(api, "audit_store", CloseTracker())
    with TestClient(api.app):
        pass
    assert closed == [True]


def _run_request_body_limit(
    max_body_bytes: int | None,
    chunks: list[bytes],
    headers: list[tuple[bytes, bytes]] | None = None,
) -> list[Message]:
    events: list[Message] = []
    index = 0

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/test",
        "raw_path": b"/test",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    async def receive() -> Message:
        nonlocal index
        if index >= len(chunks):
            return {"type": "http.disconnect"}
        chunk = chunks[index]
        index += 1
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks),
        }

    async def send(message: Message) -> None:
        events.append(message)

    async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        message = await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": message.get("body", b"")})

    middleware = RequestBodyLimitMiddleware(endpoint, max_body_bytes=max_body_bytes)
    asyncio.run(middleware(scope, receive, send))
    return events


async def _unused_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    return None


def test_request_body_limit_rejects_content_length_before_parsing() -> None:
    events = _run_request_body_limit(
        8,
        [b"123456789"],
        headers=[(b"content-length", b"9")],
    )

    assert events[0]["status"] == 413
    assert events[1]["body"] == (b'{"detail":"Request body exceeds the configured size limit"}')


def test_request_body_limit_rejects_oversized_stream_without_content_length() -> None:
    events = _run_request_body_limit(8, [b"1234", b"56789"])

    assert events[0]["status"] == 413
    assert events[1]["body"] == (b'{"detail":"Request body exceeds the configured size limit"}')


def test_request_body_limit_allows_body_at_or_below_limit() -> None:
    events = _run_request_body_limit(8, [b"1234", b"5678"])

    assert events[0]["status"] == 200
    assert events[1]["body"] == b"12345678"


def test_request_body_limit_reads_configured_environment_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ATTRACTOR_MAX_BODY_BYTES", "8")

    events = _run_request_body_limit(None, [b"123456789"])

    assert events[0]["status"] == 413


def test_request_body_limit_rejects_invalid_environment_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ATTRACTOR_MAX_BODY_BYTES", "not-a-number")

    with pytest.raises(ValueError, match="ATTRACTOR_MAX_BODY_BYTES must be a positive integer"):
        RequestBodyLimitMiddleware(_unused_asgi_app)
