"""Claim verification: caller claims are inputs; parse/mapping failures abstain."""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Protocol, Sequence
from pydantic import ValidationError
from .extraction import ClaimExtractor, ComponentProvenance, ExtractedClaim, RetrievedDocument
from .judge import ClaimJudgment, judge
from .models import Claim, Evidence, StanceEdge, Verdict
from .response import ResponseStatus
from .stance import StanceDetector

class ScopeClassifier(Protocol):
    def is_out_of_scope(self,text:str)->bool: ...

@dataclass(frozen=True)
class RuleScopeClassifier:
    forbidden_terms:tuple[str,...]=()
    def is_out_of_scope(self,text:str)->bool:
        lowered=text.casefold()
        return any(term.casefold() in lowered for term in self.forbidden_terms)

@dataclass(frozen=True)
class ClaimVerificationResult:
    query:str
    claims:tuple[ExtractedClaim,...]
    evidence:tuple[Evidence,...]
    stances:tuple[StanceEdge,...]
    judgments:tuple[ClaimJudgment,...]
    verdict:Verdict|None
    status:ResponseStatus
    confidence:float
    rationale:str
    abstention_reason:str|None=None

class ClaimVerificationPipeline:
    def __init__(self,stance_detector:StanceDetector,*,claim_extractor:ClaimExtractor|None=None,scope_classifier:ScopeClassifier|None=None)->None:
        self.claim_extractor=claim_extractor; self.stance_detector=stance_detector; self.scope_classifier=scope_classifier

    def verify(self,claims:Sequence[str],documents:Sequence[RetrievedDocument])->ClaimVerificationResult:
        normalized=tuple(str(c).strip() for c in claims if str(c).strip())
        if not normalized: raise ValueError("at least one claim is required")
        response="\n".join(normalized)
        if self.scope_classifier and self.scope_classifier.is_out_of_scope(response):
            return self._abstain(response,ResponseStatus.ABSTAIN_OUT_OF_SCOPE,"scope_rejected")
        extracted=tuple(ExtractedClaim(Claim(f"clm_{i:03d}",text),1.0,ComponentProvenance("claim_input","caller","1",self._sha(text),self._sha(text))) for i,text in enumerate(normalized,1))
        if not documents:
            return ClaimVerificationResult(response,extracted,(),(),(),None,ResponseStatus.ABSTAIN_NO_ANSWER,1.0,"No retrievable evidence was available for the supplied claims.","no_evidence")
        try:
            evidence=tuple(document.to_evidence(item.claim.id,evidence_id=f"{document.id}::{item.claim.id}") for item in extracted for document in documents)
            stance_result=self.stance_detector.detect(extracted,evidence)
            stances=tuple(item.edge for item in stance_result.edges)
            judgments,verdict=judge([item.claim for item in extracted],list(evidence),list(stances))
        except (KeyError,TypeError,ValueError,ValidationError,json.JSONDecodeError) as exc:
            return self._abstain(response,ResponseStatus.ABSTAIN_PROCESSING_ERROR,f"{type(exc).__name__}: {exc}")
        confidence=min((item.confidence for item in extracted),default=1.0)
        confidence=min(confidence,min((item.confidence for item in stance_result.edges),default=confidence))
        return ClaimVerificationResult(response,extracted,evidence,stances,tuple(judgments),verdict,ResponseStatus(verdict.value),confidence,f"Deterministic ADR-002 Judge returned {verdict.value}.")
    
    def verify_response(self,response:str,documents:Sequence[RetrievedDocument])->ClaimVerificationResult:
        if not self.claim_extractor: raise ValueError("claim_extractor is required for verify_response")
        try:
            extraction=self.claim_extractor.extract(response)
        except (KeyError,TypeError,ValueError,ValidationError,json.JSONDecodeError) as exc:
            return self._abstain(response,ResponseStatus.ABSTAIN_PROCESSING_ERROR,f"{type(exc).__name__}: {exc}")
        if not extraction.claims:
            return self._abstain(response,ResponseStatus.ABSTAIN_NO_ANSWER,"no_claims")
        return self.verify([item.claim.text for item in extraction.claims],documents)

    @staticmethod
    def _sha(value:str)->str:
        import hashlib
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _abstain(query:str,status:ResponseStatus,reason:str)->ClaimVerificationResult:
        return ClaimVerificationResult(query,(),(),(),(),None,status,1.0,f"Verification abstained: {reason}",reason)
