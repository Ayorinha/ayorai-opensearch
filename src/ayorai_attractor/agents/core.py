import logging
from dataclasses import dataclass

from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.models import AgentResult, FailureStage, FailureType
from ayorai_attractor.providers.base import Provider
from ayorai_attractor.tenant import TenantContext

logger = logging.getLogger(__name__)


def _client_safe(prefix: str, exc: Exception) -> str:
    """Failure text for API clients: the error type only.

    Exception text can carry internal endpoints and index names (an HTTP error
    names the full request URL), so it goes to the server log, never the response.
    """
    logger.warning("%s: %s: %s", prefix, type(exc).__name__, exc)
    return f"{prefix} ({type(exc).__name__}); details are in the server log."


@dataclass
class AgentContext:
    query: str
    provider: Provider
    search_provider: Provider | None
    evidence: EvidenceStore
    failures: FailureEngine
    tenant_context: TenantContext | None = None


class Agent:
    name = "agent"

    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError


class PlannerAgent(Agent):
    name = "planner"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            output=(
                "Plan: decompose the task into research, critique and "
                f"verification steps for '{context.query}'."
            ),
        )


class ResearchAgent(Agent):
    name = "research"

    def run(self, context: AgentContext) -> AgentResult:
        evidence_ids: list[str] = []
        if context.search_provider is not None:
            try:
                search_response = context.search_provider.execute(context.query)
                if search_response.documents:
                    # One evidence item per retrieved document, each with its own source.
                    for document in search_response.documents:
                        evidence_ids.append(
                            context.evidence.add(
                                claim=f"External search returned a document for '{context.query}'.",
                                source=document.source,
                                excerpt=document.content,
                                independent=search_response.independent,
                            ).id
                        )
                else:
                    search_evidence = context.evidence.add(
                        claim=f"External search returned results for '{context.query}'.",
                        source=search_response.source or "external-search",
                        excerpt=search_response.excerpt or search_response.text,
                        independent=search_response.independent,
                    )
                    evidence_ids.append(search_evidence.id)
            except Exception as exc:
                context.failures.record(
                    FailureType.API_ERROR,
                    _client_safe("External search failed", exc),
                    recoverable=True,
                    stage=FailureStage.RETRIEVAL,
                )
        try:
            response = context.provider.execute(context.query)
        except Exception as exc:
            failure = context.failures.record(
                FailureType.API_ERROR,
                _client_safe("Research provider failed", exc),
                recoverable=True,
            )
            return AgentResult(
                agent=self.name,
                output="Research provider failed; no evidence was accepted.",
                failures=[failure],
            )

        evidence = context.evidence.add(
            claim=f"Provider produced an analysis for '{context.query}'.",
            source=response.source or "unknown",
            excerpt=response.excerpt or response.text,
            independent=response.independent,
        )
        return AgentResult(
            agent=self.name,
            output=response.text,
            evidence_ids=[*evidence_ids, evidence.id],
        )


class CriticAgent(Agent):
    name = "critic"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            output=(
                "Critique: independent external verification is required "
                "before a verified conclusion."
            ),
        )


class FactCheckerAgent(Agent):
    name = "fact_checker"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            output="Fact check: no independent external source is configured in the MVP.",
        )


class JudgeAgent(Agent):
    name = "judge"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            output=(
                "Judge: result is unverified because the current evidence "
                "is local and non-independent."
            ),
        )
