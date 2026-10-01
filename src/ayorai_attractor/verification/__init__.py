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
]
