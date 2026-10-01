"""Strict verification contracts for R1."""

from .clusters import cluster_evidence, dependency_reason, has_known_dependency
from .judge import (
    ClaimJudgment,
    aggregate_verdict,
    has_complete_provenance,
    judge,
    judge_claim,
)
from .models import (
    INSUFFICIENT_EVIDENCE_TO_VERDICT,
    Claim,
    Evidence,
    Stance,
    StanceEdge,
    Verdict,
)
from .numeric import (
    DEFAULT_RELATIVE_TOLERANCE,
    DateGranularity,
    NumericLocale,
    dates_conflict,
    numeric_conflicts,
    parse_number,
    relative_difference,
)
from .response import ResponseStatus, VerificationResponse
from .security import assert_no_secret, contains_secret

__all__ = [
    "Claim",
    "Evidence",
    "Stance",
    "StanceEdge",
    "Verdict",
    "INSUFFICIENT_EVIDENCE_TO_VERDICT",
    "has_known_dependency",
    "cluster_evidence",
    "dependency_reason",
    "ClaimJudgment",
    "aggregate_verdict",
    "has_complete_provenance",
    "judge",
    "judge_claim",
    "DEFAULT_RELATIVE_TOLERANCE",
    "DateGranularity",
    "NumericLocale",
    "dates_conflict",
    "numeric_conflicts",
    "parse_number",
    "relative_difference",
    "ResponseStatus",
    "VerificationResponse",
    "assert_no_secret",
    "contains_secret",
]
