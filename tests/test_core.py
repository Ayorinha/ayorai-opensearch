from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import ayorai_attractor.orchestrator as orchestrator
from ayorai_attractor.agents.core import ResearchAgent
from ayorai_attractor.api.app import app
from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse


def test_orchestrator_is_unverified_without_external_sources() -> None:
    result = Attractor().run(SearchRequest(query="test query"))
    assert result.verification is None
    assert result.verdict_authority == "not_adjudicated"
    assert result.formal_verification_endpoint == "/v1/verify"
    assert result.operation_status in {"completed", "failed"}
    assert result.notice == (
        "No factual verdict was adjudicated. Submit structured claims and evidence "
        "to /v1/verify for formal verification."
    )


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_opensearch() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/opensearch",
        json={"query": "compare RAG and fine-tuning", "mode": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"] is None
    assert payload["verdict_authority"] == "not_adjudicated"
    assert payload["formal_verification_endpoint"] == "/v1/verify"
    assert payload["operation_status"] in {"completed", "failed"}
    assert payload["trace_id"].startswith("tr_")


def test_orchestrator_preserves_agent_output_and_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProvider(Provider):
        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(text="Provider-generated analysis.")

    monkeypatch.setattr(orchestrator, "build_default_provider", FakeProvider)
    monkeypatch.setattr(orchestrator, "build_search_provider", lambda: None)
    monkeypatch.setattr(
        orchestrator,
        "IMPLEMENTED_AGENTS",
        {"researcher": ResearchAgent},
    )

    class FakeRouter:
        def select(self, query: str, mode: str, max_agents: int) -> SimpleNamespace:
            return SimpleNamespace(roles=[SimpleNamespace(id="researcher")])

    monkeypatch.setattr(orchestrator, "AdaptiveRouter", FakeRouter)

    result = Attractor().run(SearchRequest(query="test query"))

    assert result.answer == "Provider-generated analysis."
    assert "No factual verdict was adjudicated" in result.notice
    assert result.verification is None
