"""Tests for request correlation IDs and privacy-safe access logs."""

import json
import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ayorai_attractor.api.request_context import RequestContextMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"result": "ok"}

    @app.post("/submit")
    def submit(payload: dict[str, str]) -> dict[str, str]:
        return {"result": "accepted"}

    @app.get("/failure")
    def failure() -> None:
        from fastapi import HTTPException

        raise HTTPException(status_code=418, detail="test")

    return TestClient(app)


def _events(caplog) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "ayorai_attractor.api.request_context"
    ]


def test_valid_request_id_is_preserved_and_logged(
    caplog,
) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="ayorai_attractor.api.request_context")
    with _client() as client:
        response = client.get("/private", headers={"X-Request-ID": "req-ABC-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-ABC-123"
    event = _events(caplog)[-1]
    assert event["request_id"] == "req-ABC-123"
    assert event["method"] == "GET"
    assert event["route"] == "/private"
    assert event["status"] == 200
    assert isinstance(event["duration_ms"], float | int)


def test_invalid_request_id_is_replaced(
    caplog,
) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="ayorai_attractor.api.request_context")
    with _client() as client:
        response = client.get("/private", headers={"X-Request-ID": "bad id/secret"})

    generated = response.headers["x-request-id"]
    assert generated != "bad id/secret"
    assert re.fullmatch(r"[A-Za-z0-9-]{1,64}", generated)
    assert _events(caplog)[-1]["request_id"] == generated
    assert "bad id/secret" not in caplog.text


def test_request_id_is_generated_when_missing() -> None:
    with _client() as client:
        response = client.get("/private")

    assert re.fullmatch(r"[A-Za-z0-9-]{1,64}", response.headers["x-request-id"])


def test_log_excludes_query_and_request_body(
    caplog,
) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="ayorai_attractor.api.request_context")
    sensitive_value = "must-not-appear-in-logs"
    with _client() as client:
        response = client.post(
            f"/submit?access_token={sensitive_value}",
            json={"claim": sensitive_value},
            headers={"Authorization": f"Bearer {sensitive_value}"},
        )

    assert response.status_code == 200
    event = _events(caplog)[-1]
    serialized = json.dumps(event)
    assert event["route"] == "/submit"
    assert sensitive_value not in serialized
    assert "Authorization" not in serialized
    assert "access_token" not in serialized


def test_log_records_error_status(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="ayorai_attractor.api.request_context")
    with _client() as client:
        response = client.get("/failure")

    assert response.status_code == 418
    assert _events(caplog)[-1]["status"] == 418
