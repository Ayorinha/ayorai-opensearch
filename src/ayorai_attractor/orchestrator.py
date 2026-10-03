# ruff: noqa: I001
from ayorai_attractor.agents.core import (
    AgentContext,
    CriticAgent,
    FactCheckerAgent,
    JudgeAgent,
    PlannerAgent,
    ResearchAgent,
)
from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.observability.tracing import TraceContext
from ayorai_attractor.providers.factory import build_default_provider, build_search_provider
from ayorai_attractor.providers.registry import ProviderRegistry
from ayorai_attractor.providers.base import Provider

from .models import FailureType, SearchRequest, SearchResponse, VerificationStatus
from .router import AdaptiveRouter


IMPLEMENTED_AGENTS = {
    "planner": PlannerAgent,
    "researcher": ResearchAgent,
    "critic": CriticAgent,
    "fact_checker": FactCheckerAgent,
    "chief_judge": JudgeAgent,
}


class Attractor:
    def __init__(self, search_provider: Provider | None = None) -> None:
        self.providers = ProviderRegistry()
        self.router = AdaptiveRouter()
        self.search_provider = search_provider

    def run(self, request: SearchRequest) -> SearchResponse:
        trace = TraceContext()
        trace.event("request.started", mode=request.mode.value)
        evidence = EvidenceStore()
        failures = FailureEngine()
        try:
            provider = build_default_provider()
            trace.event("provider.ready")
        except (RuntimeError, ValueError) as exc:
            failures.record(
                failure_type=FailureType.API_ERROR,
                message=str(exc),
                recoverable=False,
            )
            trace.event("request.failed", failure_type=FailureType.API_ERROR.value)
            return SearchResponse(
                query=request.query,
                mode=request.mode,
                answer=(
                    "Execution stopped because the configured provider "
                    "is unavailable."
                ),
                verification=VerificationStatus.FAILED,
                confidence=0.0,
                failures=failures.failures,
                trace_id=trace.trace_id,
            )
        context = AgentContext(
            query=request.query,
            provider=provider,
            search_provider=(
                self.search_provider
                if self.search_provider is not None
                else build_search_provider()
            ),
            evidence=evidence,
            failures=failures,
        )

        decision = self.router.select(
            query=request.query,
            mode=request.mode.value,
            max_agents=request.max_agents,
        )
        selected = [
            IMPLEMENTED_AGENTS[role.id]()
            for role in decision.roles
            if role.id in IMPLEMENTED_AGENTS
        ]
        trace.event("agents.selected", count=len(selected))
        outputs = [agent.run(context) for agent in selected]

        status = evidence.status()
        trace.event(
            "verification.completed",
            status=status.value,
            evidence_count=len(evidence.all()),
        )
        if status is VerificationStatus.UNVERIFIED:
            answer = (
                f"Preliminary result for '{request.query}'. "
                "The MVP generated a local analysis, but independent external "
                "evidence is not configured, so the result is not verified."
            )
            confidence = 0.35
        else:
            answer = outputs[-1].output if outputs else "No result."
            confidence = 0.9

        return SearchResponse(
            query=request.query,
            mode=request.mode,
            answer=answer,
            verification=status,
            confidence=confidence,
            evidence=evidence.all(),
            failures=failures.failures,
            agents_used=[agent.name for agent in selected],
            trace_id=trace.trace_id,
        )
