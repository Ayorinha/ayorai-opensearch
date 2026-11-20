"""Provider error text never reaches API clients; operators still get it in the log.

Regression: a 401 or 503 from OpenSearch returned, in the /v1/opensearch response,
"External search failed: Server error '503 Service Unavailable' for url
'https://<internal host>:<port>/<index>/_search'".
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse
from ayorai_attractor.providers.opensearch import OpenSearchProvider

HOST = "https://os-internal.corp.example:9200"
INDEX = "secret-index-name"


class _FailingResearch(Provider):
    id = "failing"

    def execute(self, prompt: str) -> ProviderResponse:
        raise RuntimeError(f"Provider request failed: 500 for url {HOST}/v1/chat")


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> TestClient:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"), mac_keys=())
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    return TestClient(app_module.app)


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 502, 503])
@pytest.mark.parametrize("path", ["/v1/opensearch", "/v1/audit", "/v2/audit"])
def test_search_http_errors_do_not_expose_the_internal_url(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: int,
    path: str,
) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, content=b"node-7 down"))
    provider = OpenSearchProvider(HOST, INDEX, api_key="k" * 40, transport=transport)
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=provider))
    with caplog.at_level(logging.WARNING, logger="ayorai_attractor"):
        response = client.post(path, json={"query": "receita da Vértice"})
    assert response.status_code == 200, response.text
    assert "os-internal" not in response.text and INDEX not in response.text
    assert "k" * 40 not in response.text and "k" * 40 not in caplog.text
    if path == "/v1/opensearch":  # the only route that returns failure messages
        messages = [failure["message"] for failure in response.json()["failures"]]
        assert messages == [
            "External search failed (HTTPStatusError); details are in the server log."
        ]
    assert f"{HOST}/{INDEX}/_search" in caplog.text  # the operator keeps the detail


def test_research_provider_errors_do_not_expose_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "ayorai_attractor.orchestrator.build_default_provider", lambda: _FailingResearch()
    )
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=None))
    with caplog.at_level(logging.WARNING, logger="ayorai_attractor"):
        response = client.post("/v1/opensearch", json={"query": "receita da Vértice"})
    assert "os-internal" not in response.text
    messages = [failure["message"] for failure in response.json()["failures"]]
    assert messages == ["Research provider failed (RuntimeError); details are in the server log."]
    assert "os-internal" in caplog.text


@pytest.mark.parametrize(
    ("error", "expected_type"),
    [
        (httpx.ConnectError("connection refused to os-internal.corp.example:9200"), "ConnectError"),
        (httpx.ReadTimeout("read timed out from os-internal.corp.example"), "ReadTimeout"),
    ],
)
def test_search_network_failures_do_not_expose_the_internal_host(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected_type: str,
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise error

    provider = OpenSearchProvider(
        HOST, INDEX, api_key="k" * 40, transport=httpx.MockTransport(fail)
    )
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=provider))
    with caplog.at_level(logging.WARNING, logger="ayorai_attractor"):
        response = client.post("/v1/opensearch", json={"query": "receita da Vértice"})
    assert response.status_code == 200, response.text
    assert "os-internal" not in response.text
    messages = [failure["message"] for failure in response.json()["failures"]]
    assert messages == [f"External search failed ({expected_type}); details are in the server log."]
    assert "os-internal" in caplog.text
