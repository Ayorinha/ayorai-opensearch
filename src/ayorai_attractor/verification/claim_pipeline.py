"""Claim-level end-to-end verification pipeline.

Retrieval and learned components are replaceable. The final verdict always
comes from the deterministic ADR-002 Judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Protocol

from .extraction import ClaimExtractor, ExtractedClaim, RetrievedDocument
from .judge import ClaimJudgment, judge
from .models import Evidence, StanceEdge, Verdict
from .response import ResponseStatus
from .stance import StanceDetector


class Retriever(Protocol):
    def retrieve(self, query: str) -> Sequence[RetrievedDocument]:
        ...


class ScopeClassifier(Protocol):
    def is_out_of_scope(self, query: str) -> bool:
        ...


@dataclass(frozen=True)
class RuleScopeClassifier:
    forbidden_terms: tuple[str, ...] = ()

    def is_out_of_scope(self, query: str) -> bool:
        lowered = query.casefold()
        return any(term.casefold() in lowered for term in self.forbidden_terms)


@dataclass(frozen=True)
class ClaimVerificationResult:
    query: str
    claims: tuple[ExtractedClaim, ...]
    evidence: tuple[Evidence, ...]
    stances: tuple[StanceEdge, ...]
    judgments: tuple[ClaimJudgment, ...]
    verdict: Verdict | None
    status: ResponseStatus
    confidence: float
    rationale: str


class ClaimVerificationPipeline:
    def __init__(
        self,
        retriever: Retriever,
        claim_extractor: ClaimExtractor,
        stance_detector: StanceDetector,
        *,
        scope_classifier: ScopeClassifier | None = None,
    ) -> None:
        self.retriever = retriever
        self.claim_extractor = claim_extractor
        self.stance_detector = stance_detector
        self.scope_classifier = scope_classifier

    def verify(self, query: str) -> ClaimVerificationResult:
        if not query.strip():
            raise ValueError("query must not be empty")

        if self.scope_classifier is not None and self.scope_classifier.is_out_of_scope(query):
            return ClaimVerificationResult(
                query=query,
                claims=(),
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_OUT_OF_SCOPE,
                confidence=1.0,
                rationale="The configured scope classifier rejected this query.",
            )

        documents = tuple(self.retriever.retrieve(query))
        if not documents:
            return ClaimVerificationResult(
                query=query,
                claims=(),
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_NO_ANSWER,
                confidence=1.0,
                rationale="No retrievable evidence was available for the query.",
            )

        extraction = self.claim_extractor.extract(query, documents)
        if not extraction.claims:
            return ClaimVerificationResult(
                query=query,
                claims=(),
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_NO_ANSWER,
                confidence=1.0,
                rationale="No verifiable claim could be extracted from the retrieved evidence.",
            )

        documents_by_id = {document.id: document for document in documents}
        evidence: list[Evidence] = []
        assigned: dict[str, str] = {}
        for item in extraction.claims:
            if not item.evidence_ids:
                raise ValueError(f"claim has no evidence mapping: {item.claim.id}")
            for evidence_id in item.evidence_ids:
                if evidence_id not in documents_by_id:
                    raise ValueError(f"claim references unknown evidence: {evidence_id}")
                if evidence_id in assigned:
                    raise ValueError(f"evidence mapped to multiple claims: {evidence_id}")
                assigned[evidence_id] = item.claim.id
                evidence.append(documents_by_id[evidence_id].to_evidence(item.claim.id))

        stance_result = self.stance_detector.detect(extraction.claims, evidence)
        stances = tuple(item.edge for item in stance_result.edges)
        judgments, verdict = judge(
            [item.claim for item in extraction.claims],
            evidence,
            list(stances),
        )
        status = ResponseStatus(verdict.value)
        claim_confidence = min(item.confidence for item in extraction.claims)
        stance_confidence = min(
            (item.confidence for item in stance_result.edges),
            default=claim_confidence,
        )
        return ClaimVerificationResult(
            query=query,
            claims=extraction.claims,
            evidence=tuple(evidence),
            stances=stances,
            judgments=tuple(judgments),
            verdict=verdict,
            status=status,
            confidence=min(claim_confidence, stance_confidence),
            rationale=(
                f"Deterministic ADR-002 Judge returned {verdict.value} from "
                f"{len(extraction.claims)} claim(s), {len(evidence)} evidence item(s) "
                f"and {len(stances)} stance edge(s)."
            ),
        )
