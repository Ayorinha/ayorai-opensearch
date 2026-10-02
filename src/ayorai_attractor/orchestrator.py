from uuid import uuid4

from ayorai_attractor.agents.core import (
    AgentContext,
    CriticAgent,
    FactCheckerAgent,
    JudgeAgent,
    PlannerAgent,
    ResearchAgent,
)
from ayorai_attractor.council import CouncilDecision, CouncilVote, deliberate
from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.providers.base import Provider
from ayorai_attractor.providers.factory import build_default_provider, build_search_provider
from ayorai_attractor.providers.registry import ProviderRegistry
from ayorai_attractor.replay import ReplayBundle
from ayorai_attractor.security import scan_untrusted_text
from ayorai_attractor.synthesis import validate_claim_citations

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
        evidence = EvidenceStore()
        failures = FailureEngine()
        trace_id = f"tr_{uuid4().hex}"
        security_findings = scan_untrusted_text(request.query)
        events: list[dict[str, object]] = [
            {"type": "request", "query": request.query, "mode": request.mode.value},
            {"type": "security_scan", "findings": [item.code for item in security_findings]},
        ]
        try:
            provider = build_default_provider()
        except (RuntimeError, ValueError) as exc:
            failures.record(
                failure_type=FailureType.API_ERROR,
                message=str(exc),
                recoverable=False,
            )
            events.append({"type": "provider_error", "message": str(exc)})
            ReplayBundle.build(trace_id, events)
            return SearchResponse(
                query=request.query,
                mode=request.mode,
                answer="Execution stopped because the configured provider is unavailable.",
                verification=VerificationStatus.FAILED,
                confidence=0.0,
                failures=failures.failures,
                trace_id=trace_id,
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
        events.append(
            {
                "type": "routing",
                "roles": [role.id for role in decision.roles],
                "reason": decision.reason,
            }
        )
        selected = [
            IMPLEMENTED_AGENTS[role.id]()
            for role in decision.roles
            if role.id in IMPLEMENTED_AGENTS
        ]
        outputs = []
        for agent in selected:
            result = agent.run(context)
            outputs.append(result)
            events.append(
                {
                    "type": "agent",
                    "agent": result.agent,
                    "evidence_ids": result.evidence_ids,
                    "failure_count": len(result.failures),
                }
            )

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

        claims = [answer]
        citation_ids = {answer: [item.id for item in evidence.all()]}
        available_evidence_ids = {item.id for item in evidence.all()}
        grounding = validate_claim_citations(
            claims, citation_ids, available_evidence_ids
        )
        if not grounding.grounded:
            events.append(
                {
                    "type": "grounding_abstention",
                    "unsupported_claims": list(grounding.unsupported_claims),
                }
            )
            if status is not VerificationStatus.FAILED:
                status = VerificationStatus.INSUFFICIENT_EVIDENCE
                confidence = 0.0
                answer = (
                    "Abstained: the available evidence does not support the generated "
                    "answer."
                )

        votes = [
            CouncilVote(
                model_id=result.agent,
                decision=(
                    CouncilDecision.SUPPORTED
                    if status in {VerificationStatus.VERIFIED, VerificationStatus.SUPPORTED}
                    else CouncilDecision.ABSTAIN
                ),
                rationale="Derived from the deterministic evidence status.",
            )
            for agent in outputs
        ]
        council = deliberate(votes)
        events.append(
            {
                "type": "council",
                "decision": council.decision.value,
                "agreement_ratio": council.agreement_ratio,
            }
        )
        replay = ReplayBundle.build(trace_id, events)
        events.append({"type": "replay_digest", "digest": replay.digest})
        return SearchResponse(
            query=request.query,
            mode=request.mode,
            answer=answer,
            verification=status,
            confidence=confidence,
            evidence=evidence.all(),
            failures=failures.failures,
            agents_used=[agent.name for agent in selected],
            trace_id=trace_id,
        )
