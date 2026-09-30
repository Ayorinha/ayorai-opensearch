# ruff: noqa: I001
from uuid import uuid4

from agents.core import (
    AgentContext,
    CriticAgent,
    FactCheckerAgent,
    JudgeAgent,
    PlannerAgent,
    ResearchAgent,
)
from evidence.core import EvidenceStore
from failure_engine.core import FailureEngine
from providers.factory import build_default_provider
from providers.registry import ProviderRegistry

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
    def __init__(self) -> None:
        self.providers = ProviderRegistry()
        self.router = AdaptiveRouter()

    def run(self, request: SearchRequest) -> SearchResponse:
        evidence = EvidenceStore()
        failures = FailureEngine()
        try:
            provider = build_default_provider()
        except (RuntimeError, ValueError) as exc:
            failures.record(
                failure_type=FailureType.API_ERROR,
                message=str(exc),
                recoverable=False,
            )
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
                trace_id=f"tr_{uuid4().hex}",
            )
        context = AgentContext(
            query=request.query,
            provider=provider,
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
        outputs = [agent.run(context) for agent in selected]

        status = evidence.status()
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
            trace_id=f"tr_{uuid4().hex}",
        )
