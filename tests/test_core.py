from types import SimpleNamespace

from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
import ayorai_attractor.orchestrator as orchestrator
from ayorai_attractor.models import AgentResult, SearchRequest
from ayorai_attractor.orchestrator import Attractor


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


def test_orchestrator_preserves_agent_output_and_notice(monkeypatch) -> None:
    class FakeAgent:
        name = "fake"

        def run(self, context: object) -> AgentResult:
            return AgentResult(agent=self.name, output="Provider-generated analysis.")

    monkeypatch.setattr(orchestrator, "build_default_provider", lambda: object())
    monkeypatch.setattr(orchestrator, "build_search_provider", lambda: None)
    monkeypatch.setattr(
        orchestrator,
        "IMPLEMENTED_AGENTS",
        {"planner": FakeAgent},
    )
    monkeypatch.setattr(
        orchestrator,
        "AdaptiveRouter",
        lambda: SimpleNamespace(
            select=lambda **kwargs: SimpleNamespace(
                roles=[SimpleNamespace(id="planner")]
            )
        ),
    )

    result = Attractor().run(SearchRequest(query="test query"))

    assert result.answer == "Provider-generated analysis."
    assert "No factual verdict was adjudicated" in result.notice
    assert result.verification is None
