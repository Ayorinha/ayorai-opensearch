"""Deterministic audit report for R2 Audit Mode.

Audit Mode does not change a verdict. It exposes the evidence, provenance,
failures, and verification signals that led to the current response.
"""

from dataclasses import dataclass
from enum import StrEnum

from ayorai_attractor.models import Evidence, Failure, SearchResponse


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: AuditSeverity
    message: str


@dataclass(frozen=True)
class AuditReport:
    trace_id: str
    verification: str
    evidence_count: int
    independent_evidence_count: int
    verified_evidence_count: int
    failure_count: int
    findings: tuple[AuditFinding, ...]

    @classmethod
    def from_response(cls, response: SearchResponse) -> "AuditReport":
        findings: list[AuditFinding] = []
        evidence = response.evidence
        independent = [item for item in evidence if item.independent]
        verified = [item for item in evidence if item.verified]

        if not evidence:
            findings.append(
                AuditFinding(
                    "NO_EVIDENCE",
                    AuditSeverity.ERROR,
                    "Response contains no evidence items.",
                )
            )
        elif len(independent) < 2:
            findings.append(
                AuditFinding(
                    "WEAK_INDEPENDENCE",
                    AuditSeverity.WARNING,
                    "Fewer than two evidence items are marked independent.",
                )
            )

        if not verified:
            findings.append(
                AuditFinding(
                    "NO_VERIFIED_EVIDENCE",
                    AuditSeverity.WARNING,
                    "No evidence item is marked verified.",
                )
            )

        for failure in response.failures:
            findings.append(_failure_finding(failure))

        if response.verification.value in {"failed", "insufficient_evidence"}:
            findings.append(
                AuditFinding(
                    "NON_VERIFIED_RESPONSE",
                    AuditSeverity.ERROR,
                    f"Verification status is {response.verification.value}.",
                )
            )

        return cls(
            trace_id=response.trace_id,
            verification=response.verification.value,
            evidence_count=len(evidence),
            independent_evidence_count=len(independent),
            verified_evidence_count=len(verified),
            failure_count=len(response.failures),
            findings=tuple(findings),
        )


def _failure_finding(failure: Failure) -> AuditFinding:
    severity = AuditSeverity.ERROR if not failure.recoverable else AuditSeverity.WARNING
    return AuditFinding(
        code=f"FAILURE_{failure.type.value.upper()}",
        severity=severity,
        message=failure.message,
    )


def audit_evidence(
    evidence: list[Evidence],
    failures: list[Failure] | None = None,
) -> tuple[AuditFinding, ...]:
    """Audit evidence directly for callers without a SearchResponse."""
    response = SearchResponse(
        query="audit",
        mode="balanced",
        answer="audit",
        verification="unverified",
        confidence=0.0,
        evidence=evidence,
        failures=failures or [],
        agents_used=[],
        trace_id="audit",
    )
    return AuditReport.from_response(response).findings
