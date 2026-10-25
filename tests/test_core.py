from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import ayorai_attractor.orchestrator as orchestrator
from ayorai_attractor.agents.core import AgentContext, ResearchAgent
from ayorai_attractor.api.app import app
from ayorai_attractor.models import AgentResult, FailureType, SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse
from ayorai_attractor.tenant import TenantContext


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


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("provider unavailable"),
        ValueError("provider configuration invalid"),
    ],
)
def test_orchestrator_returns_failed_response_when_provider_setup_fails(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def fail_provider() -> Provider:
        raise error

    monkeypatch.setattr(orchestrator, "build_default_provider", fail_provider)

    result = Attractor().run(SearchRequest(query="provider setup failure"))

    assert result.operation_status == "failed"
    assert result.verification is None
    assert result.verdict_authority == "not_adjudicated"
    assert len(result.failures) == 1
    assert result.failures[0].type is FailureType.API_ERROR
    assert result.failures[0].recoverable is False
    assert str(error) in result.failures[0].message


def test_orchestrator_filters_unknown_roles_and_propagates_tenant_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProvider(Provider):
        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(text="unused")

    captured_contexts: list[AgentContext] = []

    class CapturingAgent:
        name = "capturing"

        def run(self, context: AgentContext) -> AgentResult:
            captured_contexts.append(context)
            return AgentResult(agent=self.name, output="Captured tenant context.")

    class FakeRouter:
        def select(self, query: str, mode: str, max_agents: int) -> SimpleNamespace:
            return SimpleNamespace(
                roles=[
                    SimpleNamespace(id="not_implemented"),
                    SimpleNamespace(id="capturing"),
                ]
            )

    tenant = TenantContext(
        tenant_id="tenant-1",
        subject_id="subject-1",
        authorization_scope="read:documents",
    )
    monkeypatch.setattr(orchestrator, "build_default_provider", FakeProvider)
    monkeypatch.setattr(orchestrator, "build_search_provider", lambda: None)
    monkeypatch.setattr(orchestrator, "IMPLEMENTED_AGENTS", {"capturing": CapturingAgent})
    monkeypatch.setattr(orchestrator, "AdaptiveRouter", FakeRouter)

    result = Attractor().run(
        SearchRequest(query="tenant propagation"),
        tenant_context=tenant,
    )

    assert result.answer == "Captured tenant context."
    assert result.agents_used == ["capturing"]
    assert len(captured_contexts) == 1
    assert captured_contexts[0].tenant_context is tenant


def test_orchestrator_uses_fallback_answer_when_no_implemented_agent_is_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProvider(Provider):
        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(text="unused")

    class FakeRouter:
        def select(self, query: str, mode: str, max_agents: int) -> SimpleNamespace:
            return SimpleNamespace(roles=[SimpleNamespace(id="not_implemented")])

    monkeypatch.setattr(orchestrator, "build_default_provider", FakeProvider)
    monkeypatch.setattr(orchestrator, "build_search_provider", lambda: None)
    monkeypatch.setattr(orchestrator, "IMPLEMENTED_AGENTS", {})
    monkeypatch.setattr(orchestrator, "AdaptiveRouter", FakeRouter)

    result = Attractor().run(SearchRequest(query="no supported agent"))

    assert result.answer == (
        "Analysis completed for 'no supported agent'. No agent produced output."
    )
    assert result.operation_status == "completed"
    assert result.agents_used == []


def test_orchestrator_marks_terminal_failure_and_uses_fallback_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProvider(Provider):
        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(text="unused")

    class SilentFailingAgent:
        name = "silent_failure"

        def run(self, context: AgentContext) -> AgentResult:
            context.failures.record(
                FailureType.API_ERROR,
                "terminal agent failure",
                recoverable=False,
            )
            return AgentResult(agent=self.name, output="  ")

    class FakeRouter:
        def select(self, query: str, mode: str, max_agents: int) -> SimpleNamespace:
            return SimpleNamespace(roles=[SimpleNamespace(id="silent_failure")])

    monkeypatch.setattr(orchestrator, "build_default_provider", FakeProvider)
    monkeypatch.setattr(orchestrator, "build_search_provider", lambda: None)
    monkeypatch.setattr(
        orchestrator,
        "IMPLEMENTED_AGENTS",
        {"silent_failure": SilentFailingAgent},
    )
    monkeypatch.setattr(orchestrator, "AdaptiveRouter", FakeRouter)

    result = Attractor().run(SearchRequest(query="terminal failure"))

    assert result.answer == ("Analysis completed for 'terminal failure'. No agent produced output.")
    assert result.operation_status == "failed"
    assert result.failures[0].recoverable is False
    assert result.agents_used == ["silent_failure"]
