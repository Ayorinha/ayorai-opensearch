"""Readiness, liveness and Prometheus metrics (GET /ready, /health, /metrics)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api.http_metrics import HttpMetrics
from ayorai_attractor.audit_store import AuditTraceStore


def _digest(key: str, pepper_hex: str) -> str:
    return hmac.new(bytes.fromhex(pepper_hex), key.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
def service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> dict[str, Any]:
    pepper = secrets.token_hex(32)
    key = secrets.token_urlsafe(32)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", pepper)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key, pepper))
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    metrics = HttpMetrics()
    monkeypatch.setattr(app_module, "http_metrics", metrics)
    monkeypatch.setattr("ayorai_attractor.api.request_context.http_metrics", metrics)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    return {
        "client": TestClient(app_module.app),
        "auth": {"Authorization": f"Bearer {key}"},
        "store": store,
        "metrics": metrics,
    }


def test_readiness_answers_without_a_key(service: dict[str, Any]) -> None:
    response = service["client"].get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_fails_when_the_audit_store_does_not_answer(
    service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service["store"], "ping", lambda: False)
    response = service["client"].get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_readiness_reports_a_closed_database_as_not_ready(tmp_path: Path) -> None:
    store = AuditTraceStore(str(tmp_path / "a.sqlite3"))
    assert store.ping() is True
    store.close()
    assert store.ping() is False


def test_liveness_does_not_depend_on_the_audit_store(
    service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service["store"], "ping", lambda: False)
    assert service["client"].get("/health").status_code == 200


def test_metrics_require_the_api_key(service: dict[str, Any]) -> None:
    assert service["client"].get("/metrics").status_code == 401
    response = service["client"].get("/metrics", headers=service["auth"])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attractor_build_info" in response.text


def test_metrics_count_requests_with_bounded_labels(service: dict[str, Any]) -> None:
    client = service["client"]
    client.post("/v1/audit", json={"query": "receita da Vértice"}, headers=service["auth"])
    client.get("/v1/audit/tr_secret_looking_id", headers=service["auth"])
    client.get("/client/chosen/path", headers=service["auth"])
    client.post("/v2/audit", json={})  # rejected before routing: 401
    text = service["metrics"].render()
    assert 'route="/v1/audit",method="POST",status="200"' in text
    assert 'route="/v1/audit/{trace_id}",method="GET",status="404"' in text
    assert 'route="unmatched",method="GET",status="404"' in text
    assert 'route="/v2/audit",method="POST",status="401"' in text
    # Neither the trace ID nor the client-chosen path nor the key becomes a label.
    assert "tr_secret_looking_id" not in text
    assert "client/chosen" not in text
    assert 'attractor_http_request_duration_seconds_count{route="/v1/audit"} 1' in text


def test_audit_record_failures_are_counted_and_still_fail_the_request(
    service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(*args: object, **kwargs: object) -> str:
        raise RuntimeError("disk full")

    monkeypatch.setattr(service["store"], "record", failing)
    client = TestClient(app_module.app, raise_server_exceptions=False)
    response = client.post("/v1/audit", json={"query": "receita"}, headers=service["auth"])
    assert response.status_code == 500
    assert "attractor_audit_record_failures_total 1" in service["metrics"].render()


def test_histogram_buckets_are_cumulative() -> None:
    metrics = HttpMetrics(buckets=(0.1, 1.0))
    metrics.observe("/health", "GET", 200, 0.05)
    metrics.observe("/health", "GET", 200, 0.5)
    metrics.observe("/health", "GET", 200, 5.0)
    text = metrics.render()
    assert 'attractor_http_request_duration_seconds_bucket{route="/health",le="0.1"} 1' in text
    assert 'attractor_http_request_duration_seconds_bucket{route="/health",le="1"} 2' in text
    assert 'attractor_http_request_duration_seconds_bucket{route="/health",le="+Inf"} 3' in text


def test_invalid_buckets_are_rejected() -> None:
    with pytest.raises(ValueError):
        HttpMetrics(buckets=(1.0, 0.5))


def test_client_chosen_methods_cannot_create_unbounded_series() -> None:
    metrics = HttpMetrics()
    for index in range(50):
        metrics.observe("unmatched", f"X-METHOD-{index}", 405, 0.001)
    text = metrics.render()
    assert 'method="OTHER",status="405"} 50' in text
    assert "X-METHOD" not in text
