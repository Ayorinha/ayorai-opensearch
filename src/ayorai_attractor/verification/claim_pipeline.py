"""Claim-level verification: claims are inputs; evidence is never a claim source."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from .extraction import (
    ClaimExtractor,
    ComponentProvenance,
    ExtractedClaim,
    RetrievedDocument,
)
from .excerpt import revalidate_evidence
from .judge import ClaimJudgment, judge
from .models import Claim, Evidence, StanceEdge, Verdict
from .response import ResponseStatus
from .stance import StanceDetector


class ScopeClassifier(Protocol):
    def is_out_of_scope(self, text: str) -> bool:
        ...


@dataclass(frozen=True)
class RuleScopeClassifier:
    forbidden_terms: tuple[str, ...] = ()

    def is_out_of_scope(self, text: str) -> bool:
        lowered = text.casefold()
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
    abstention_reason: str | None = None
    audit_reasons: tuple[str, ...] = ()


class ClaimVerificationPipeline:
    def __init__(
        self,
        stance_detector: StanceDetector,
        *,
        claim_extractor: ClaimExtractor | None = None,
        scope_classifier: ScopeClassifier | None = None,
    ) -> None:
        self.claim_extractor = claim_extractor
        self.stance_detector = stance_detector
        self.scope_classifier = scope_classifier

    def verify(
        self,
        claims: Sequence[str],
        documents: Sequence[RetrievedDocument],
        sources: Mapping[str, str] | None = None,
    ) -> ClaimVerificationResult:
        """Verify caller-supplied claims against the closed-world documents.

        The claim text is authoritative input. No verdict or claim text is
        derived from document content.
        """
        normalized = tuple(str(claim).strip() for claim in claims if str(claim).strip())
        if not normalized:
            raise ValueError("at least one claim is required")

        response = "\n".join(normalized)
        if self.scope_classifier is not None and self.scope_classifier.is_out_of_scope(response):
            return ClaimVerificationResult(
                query=response,
                claims=(),
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_OUT_OF_SCOPE,
                confidence=1.0,
                rationale="The configured scope classifier rejected the claims.",
            )

        extracted = tuple(
            ExtractedClaim(
                claim=Claim(id=f"clm_{index:03d}", text=text),
                confidence=1.0,
                provenance=_input_provenance(text),
            )
            for index, text in enumerate(normalized, start=1)
        )
        if not documents:
            return ClaimVerificationResult(
                query=response,
                claims=extracted,
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_NO_ANSWER,
                confidence=1.0,
                rationale="No retrievable evidence was available for the supplied claims.",
            )

        evidence_items = [
            document.to_evidence(
                item.claim.id,
                evidence_id=f"{document.id}::{item.claim.id}",
            )
            for item in extracted
            for document in documents
        ]
        audit_reasons: list[str] = []
        if sources is not None:
            revalidated: list[Evidence] = []
            for item in evidence_items:
                source_text = sources.get(item.source_id, "")
                checked = revalidate_evidence(item, source_text)
                if checked is None:
                    audit_reasons.append("excerpt_not_in_source")
                    continue
                revalidated.append(checked)
            evidence = tuple(revalidated)
        else:
            evidence = tuple(evidence_items)
        try:
            stance_result = self.stance_detector.detect(extracted, evidence)
            stances = tuple(item.edge for item in stance_result.edges)
            judgments, verdict = judge(
                [item.claim for item in extracted],
                list(evidence),
                list(stances),
            )
        except (ValidationError, ValueError) as exc:
            return ClaimVerificationResult(
                query=response,
                claims=extracted,
                evidence=evidence,
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_PROCESSING_ERROR,
                confidence=1.0,
                rationale=f"{type(exc).__name__}: {exc}",
                abstention_reason=type(exc).__name__,
                audit_reasons=tuple(audit_reasons),
            )
        confidence = min(
            (item.confidence for item in extracted),
            default=1.0,
        )
        confidence = min(
            confidence,
            min((item.confidence for item in stance_result.edges), default=confidence),
        )
        return ClaimVerificationResult(
            query=response,
            claims=extracted,
            evidence=evidence,
            stances=stances,
            judgments=tuple(judgments),
            verdict=verdict,
            status=ResponseStatus(verdict.value),
            confidence=confidence,
            audit_reasons=tuple(audit_reasons),
            rationale=(
                f"Deterministic ADR-002 Judge returned {verdict.value} from "
                f"{len(extracted)} claim(s), {len(evidence)} evidence item(s) "
                f"and {len(stances)} stance edge(s)."
            ),
        )

    def verify_response(
        self,
        response: str,
        documents: Sequence[RetrievedDocument],
        sources: Mapping[str, str] | None = None,
    ) -> ClaimVerificationResult:
        """Decompose a model response, then verify the resulting claims."""
        if self.claim_extractor is None:
            raise ValueError("claim_extractor is required for verify_response")
        extraction = self.claim_extractor.extract(response)
        if not extraction.claims:
            return ClaimVerificationResult(
                query=response,
                claims=(),
                evidence=(),
                stances=(),
                judgments=(),
                verdict=None,
                status=ResponseStatus.ABSTAIN_NO_ANSWER,
                confidence=1.0,
                rationale="No atomic claim could be extracted from the response.",
            )
        return self.verify(
            [item.claim.text for item in extraction.claims],
            documents,
            sources=sources,
        )


def _input_provenance(text: str) -> ComponentProvenance:
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ComponentProvenance(
        component="claim_input",
        model="caller",
        version="1",
        input_sha256=digest,
        output_sha256=digest,
    )
