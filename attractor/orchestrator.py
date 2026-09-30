from uuid import uuid4

from agents.core import (
    AgentContext,
    CriticAgent,
    FactCheckerAgent,
    JudgeAgent,
    PlannerAgent,
    ResearchAgent,
)
from attractor.models import SearchRequest, SearchResponse, VerificationStatus
from evidence.core import EvidenceStore
from failure_engine.core import FailureEngine
from providers.registry import ProviderRegistry


class Attractor:
    def __init__(self) -> None:
        self.providers = ProviderRegistry()

    def run(self, request: SearchRequest) -> SearchResponse:
        evidence = EvidenceStore()
        failures = FailureEngine()
        provider = self.providers.get("mock")
        context = AgentContext(
            query=request.query,
            provider=provider,
            evidence=evidence,
        )

        agents = [
            PlannerAgent(),
            ResearchAgent(),
            CriticAgent(),
            FactCheckerAgent(),
            JudgeAgent(),
        ]
        selected = agents[: min(request.max_agents, len(agents))]
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
