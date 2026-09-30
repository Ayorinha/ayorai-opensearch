from dataclasses import dataclass

from ayorai_attractor.evidence.core import EvidenceStore
from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.models import AgentResult, FailureType
from ayorai_attractor.providers.base import Provider


@dataclass
class AgentContext:
    query: str
    provider: Provider
    search_provider: Provider | None
    evidence: EvidenceStore
    failures: FailureEngine


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
                    f"External search failed: {exc}",
                    recoverable=True,
                )
        try:
            response = context.provider.execute(context.query)
        except Exception as exc:
            failure = context.failures.record(
                FailureType.API_ERROR,
                f"Research provider failed: {exc}",
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
