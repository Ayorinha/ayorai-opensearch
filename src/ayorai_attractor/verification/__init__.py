"""Strict verification contracts for R1."""

from .claim_pipeline import ClaimVerificationPipeline, ClaimVerificationResult, RuleScopeClassifier
from .clusters import cluster_evidence, dependency_reason, has_known_dependency
from .extraction import ClaimExtractionResult, ClaimExtractor, ComponentProvenance, ExtractedClaim, LLMClaimExtractor, NLIClaimExtractor, RetrievedDocument, RuleClaimExtractor
from .judge import ClaimJudgment, aggregate_verdict, has_complete_provenance, judge, judge_claim
from .models import INSUFFICIENT_EVIDENCE_TO_VERDICT, Claim, Evidence, Stance, StanceEdge, Verdict
from .numeric import DEFAULT_RELATIVE_TOLERANCE, DateGranularity, NumericLocale, dates_conflict, numeric_conflicts, parse_number, relative_difference
from .response import ResponseStatus, VerificationResponse
from .security import assert_no_secret, contains_secret
from .stance import DetectedStance, LLMStanceDetector, NLIStanceDetector, RuleStanceDetector, StanceDetectionResult, StanceDetector

__all__ = [
    "Claim", "ClaimVerificationPipeline", "ClaimVerificationResult", "RuleScopeClassifier", "ComponentProvenance", "RetrievedDocument", "ExtractedClaim", "ClaimExtractionResult", "ClaimExtractor", "RuleClaimExtractor", "NLIClaimExtractor", "LLMClaimExtractor", "DetectedStance", "StanceDetectionResult", "StanceDetector", "RuleStanceDetector", "NLIStanceDetector", "LLMStanceDetector", "Evidence", "Stance", "StanceEdge", "Verdict", "INSUFFICIENT_EVIDENCE_TO_VERDICT", "has_known_dependency", "cluster_evidence", "dependency_reason", "ClaimJudgment", "aggregate_verdict", "has_complete_provenance", "judge", "judge_claim", "DEFAULT_RELATIVE_TOLERANCE", "DateGranularity", "NumericLocale", "dates_conflict", "numeric_conflicts", "parse_number", "relative_difference", "ResponseStatus", "VerificationResponse", "assert_no_secret", "contains_secret",
]
