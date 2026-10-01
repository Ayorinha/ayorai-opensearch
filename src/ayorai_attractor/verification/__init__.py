"""Strict verification contracts for R1."""

from .clusters import cluster_evidence, dependency_reason, has_known_dependency
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
    "DEFAULT_RELATIVE_TOLERANCE",
    "DateGranularity",
    "NumericLocale",
    "dates_conflict",
    "numeric_conflicts",
    "parse_number",
    "relative_difference",
]
