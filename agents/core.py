from dataclasses import dataclass

from attractor.models import AgentResult, FailureType
from evidence.core import EvidenceStore
from failure_engine.core import FailureEngine
from providers.base import Provider


@dataclass
class AgentContext:
    query: str
    provider: Provider
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
        )
        return AgentResult(
            agent=self.name,
            output=response.text,
            evidence_ids=[evidence.id],
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
