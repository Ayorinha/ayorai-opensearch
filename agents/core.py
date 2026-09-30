from dataclasses import dataclass

from attractor.models import AgentResult
from evidence.core import EvidenceStore
from providers.base import Provider


@dataclass
class AgentContext:
    query: str
    provider: Provider
    evidence: EvidenceStore


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
        response = context.provider.execute(context.query)
        evidence = context.evidence.add(
            claim=f"Local provider produced an analysis for '{context.query}'.",
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
