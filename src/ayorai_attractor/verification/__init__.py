"""Strict verification contracts for R1."""

from .clusters import are_independent, cluster_evidence, dependency_reason
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
    "are_independent",
    "cluster_evidence",
    "dependency_reason",
]
