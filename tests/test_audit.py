from ayorai_attractor.audit import AuditReport, AuditSeverity
from ayorai_attractor.models import Evidence, SearchResponse, VerificationStatus


def response(
    evidence: list[Evidence],
    status: VerificationStatus = VerificationStatus.UNVERIFIED,
) -> SearchResponse:
    return SearchResponse(
        query="test",
        mode="balanced",
        answer="test",
        verification=status,
        confidence=0.1,
        evidence=evidence,
        failures=[],
        agents_used=[],
        trace_id="tr_test",
    )


def test_audit_flags_missing_evidence() -> None:
    report = AuditReport.from_response(response([]))
    assert report.evidence_count == 0
    assert any(item.code == "NO_EVIDENCE" for item in report.findings)
    assert any(item.severity is AuditSeverity.ERROR for item in report.findings)


def test_audit_reports_independence_and_verification_counts() -> None:
    evidence = [
        Evidence(
            id="e1",
            claim="claim",
            source="source-a",
            excerpt="excerpt",
            independent=True,
            verified=True,
        ),
        Evidence(
            id="e2",
            claim="claim",
            source="source-b",
            excerpt="excerpt",
            independent=True,
            verified=False,
        ),
    ]
    report = AuditReport.from_response(response(evidence, VerificationStatus.SUPPORTED))
    assert report.independent_evidence_count == 2
    assert report.verified_evidence_count == 1
    assert report.failure_count == 0
    assert report.findings == ()
