from typing import Literal

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
from ayorai_attractor.providers.base import Provider
from ayorai_attractor.providers.factory import build_default_provider, build_search_provider
from ayorai_attractor.providers.registry import ProviderRegistry

from .models import FailureType, SearchRequest, SearchResponse
from .router import AdaptiveRouter
from .tenant import TenantContext

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

    def run(
        self,
        request: SearchRequest,
        *,
        tenant_context: TenantContext | None = None,
    ) -> SearchResponse:
        trace = TraceContext()
        trace.event("request.started", mode=request.mode.value)
        if tenant_context is not None:
            trace.event(
                "tenant.context.bound",
                tenant_id=tenant_context.tenant_id,
                authorization_scope=tenant_context.authorization_scope,
            )
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
                verification=None,
                operation_status="failed",
                confidence=None,
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
            tenant_context=tenant_context,
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

        trace.event(
            "analysis.completed",
            evidence_count=len(evidence.all()),
        )
        answer = next(
            (item.output for item in reversed(outputs) if item.output.strip()),
            f"Analysis completed for '{request.query}'. No agent produced output.",
        )
        operation_status: Literal["completed", "failed", "not_recorded"] = (
            "failed"
            if any(not failure.recoverable for failure in failures.failures)
            else "completed"
        )

        return SearchResponse(
            query=request.query,
            mode=request.mode,
            answer=answer,
            verification=None,
            verdict_authority="not_adjudicated",
            formal_verification_endpoint="/v1/verify",
            operation_status=operation_status,
            confidence=None,
            evidence=evidence.all(),
            failures=failures.failures,
            agents_used=[agent.name for agent in selected],
            trace_id=trace.trace_id,
        )
