"""A JSON body that is not valid UTF-8 is a JSON decode error (422), never 400.

Found by Schemathesis: FastAPI answers 400 when ``json.loads(bytes)`` raises
UnicodeDecodeError, a status the OpenAPI document does not declare.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module

POST_ROUTES = ["/v1/check", "/v1/fields", "/v1/verify", "/v1/audit", "/v1/opensearch"]
BODIES = [b"\xff#\xff{", b'{"claims": ["\xc3\x28"]}', b"\x80", b"\xed\xa0\x80"]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    return TestClient(app_module.app)


@pytest.mark.parametrize("route", POST_ROUTES)
@pytest.mark.parametrize("body", BODIES)
def test_invalid_utf8_is_json_invalid(client: TestClient, route: str, body: bytes) -> None:
    response = client.post(route, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    (error,) = response.json()["detail"]
    assert error["type"] == "json_invalid"
    assert error["loc"][0] == "body" and isinstance(error["loc"][1], int)


def test_malformed_utf8_json_keeps_the_existing_envelope(client: TestClient) -> None:
    response = client.post(
        "/v1/check", content=b"{bad", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_other_http_errors_are_unchanged(client: TestClient) -> None:
    missing = client.get("/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Not Found"}
    wrong_method = client.get("/v1/check")
    assert wrong_method.status_code == 405
    assert wrong_method.json() == {"detail": "Method Not Allowed"}
    assert wrong_method.headers["allow"] == "POST"


def test_no_documented_route_returns_400() -> None:
    schema = app_module.app.openapi()
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert "400" not in operation.get("responses", {}), (method, path)
