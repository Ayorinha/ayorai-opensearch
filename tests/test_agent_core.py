import pytest

from ayorai_attractor.agents.core import Agent, AgentContext, ResearchAgent
from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.models import FailureType
from ayorai_attractor.providers.base import Provider, ProviderResponse


class StaticProvider(Provider):
    id = "static"

    def execute(self, prompt: str) -> ProviderResponse:
        return ProviderResponse(
            text="deterministic test response",
            source="unit-test",
            excerpt="deterministic test excerpt",
        )


class FailingProvider(Provider):
    id = "failing"

    def execute(self, prompt: str) -> ProviderResponse:
        raise RuntimeError("synthetic provider failure")


def make_context(
    *,
    provider: Provider,
    search_provider: Provider | None = None,
) -> AgentContext:
    return AgentContext(
        query="synthetic query",
        provider=provider,
        search_provider=search_provider,
        evidence=EvidenceStore(),
        failures=FailureEngine(),
    )


def test_base_agent_run_is_not_implemented() -> None:
    context = make_context(provider=StaticProvider())

    with pytest.raises(NotImplementedError):
        Agent().run(context)


def test_research_agent_continues_after_search_provider_failure() -> None:
    context = make_context(
        provider=StaticProvider(),
        search_provider=FailingProvider(),
    )

    result = ResearchAgent().run(context)

    assert result.output == "deterministic test response"
    assert len(result.evidence_ids) == 1
    assert len(context.evidence.all()) == 1
    assert len(context.failures.failures) == 1
    failure = context.failures.failures[0]
    assert failure.type is FailureType.API_ERROR
    assert failure.recoverable is True
    assert "External search failed" in failure.message


def test_research_agent_returns_failure_when_primary_provider_fails() -> None:
    context = make_context(provider=FailingProvider())

    result = ResearchAgent().run(context)

    assert result.output == "Research provider failed; no evidence was accepted."
    assert result.evidence_ids == []
    assert result.failures == context.failures.failures
    assert len(context.failures.failures) == 1
    failure = context.failures.failures[0]
    assert failure.type is FailureType.API_ERROR
    assert failure.recoverable is True
    assert "Research provider failed" in failure.message
    assert context.evidence.all() == []
