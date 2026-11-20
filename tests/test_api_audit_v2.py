"""POST /v2/audit: search, then adjudicate claims against independent sources only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse

FACT = "A receita da Vértice foi de 40 milhões em 2024."


class _Search(Provider):
    id = "fake-search"

    def __init__(self, excerpt: str, *, independent: bool = True) -> None:
        self.excerpt = excerpt
        self.independent = independent

    def execute(self, prompt: str) -> ProviderResponse:
        return ProviderResponse(
            text=self.excerpt,
            source="https://example.test/balanco-2024",
            excerpt=self.excerpt,
            independent=self.independent,
        )


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


def _use_search(monkeypatch: pytest.MonkeyPatch, excerpt: str, *, independent: bool = True) -> None:
    monkeypatch.setattr(
        app_module, "engine", Attractor(search_provider=_Search(excerpt, independent=independent))
    )


def _post(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/v2/audit", json=body)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()
    return data


def test_without_independent_sources_every_claim_abstains_and_the_trace_is_stored(
    client: TestClient,
) -> None:
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?", "claims": [FACT]})
    assert data["schema_version"] == "a2"
    assert data["claims_source"] == "caller_claims"
    assert data["check_trace_id"] is None and data["documents"] == []
    (result,) = data["results"]
    assert result["verdict"] is None
    assert result["abstention_reason"] == "no_independent_source"
    stored = client.get(f"/v1/audit/{data['trace_id']}")
    assert stored.status_code == 200
    assert stored.json()["replay_integrity"] == "valid"


def test_a_confirming_independent_source_supports_the_claim(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_search(monkeypatch, "Segundo o balanço, a receita da Vértice foi de 40 milhões em 2024.")
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?", "claims": [FACT]})
    (result,) = data["results"]
    assert result["status"] == "partially_supported"
    assert [item["stance"] for item in result["evidence"]] == ["supports"]
    assert data["check_trace_id"].startswith("chk_")
    assert data["engine"]["judge"] == "ADR-002"
    assert len(data["documents"]) == 1


def test_a_contradicting_independent_source_refutes_the_claim(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_search(monkeypatch, "Segundo o balanço, a receita da Vértice foi de 55 milhões em 2024.")
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?", "claims": [FACT]})
    assert data["results"][0]["verdict"] == "refuted"


def test_model_output_is_never_used_as_evidence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_search(monkeypatch, FACT, independent=False)
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?", "claims": [FACT]})
    assert data["documents"] == []
    assert data["results"][0]["abstention_reason"] == "no_independent_source"


def test_a_caller_answer_is_decomposed_into_claims(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_search(monkeypatch, "Segundo o balanço, a receita da Vértice foi de 40 milhões em 2024.")
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?", "answer": FACT})
    assert data["claims_source"] == "caller_answer"
    assert data["results"] and data["results"][0]["claim"]


def test_by_default_the_engine_answer_is_checked(client: TestClient) -> None:
    data = _post(client, {"query": "Qual foi a receita da Vértice em 2024?"})
    assert data["claims_source"] == "engine_answer"
    assert data["answer"]
    assert data["operation_status"] == "completed"


@pytest.mark.parametrize(
    "body",
    [
        {"query": "receita", "claims": [FACT], "answer": FACT},
        {"query": "receita", "extra": 1},
        {"query": "  "},
        {"query": "receita", "claims": []},
        {"query": "receita", "mode": "turbo"},
    ],
)
def test_invalid_requests_are_rejected(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/v2/audit", json=body).status_code == 422


def test_v2_audit_requires_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", "ab" * 32)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", "cd" * 32)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    response = TestClient(app_module.app).post("/v2/audit", json={"query": "receita"})
    assert response.status_code == 401
