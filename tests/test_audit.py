from ayorai_attractor.audit import AuditReport, AuditSeverity, audit_evidence
from ayorai_attractor.models import Evidence, Failure, FailureType, SearchResponse


def response(evidence: list[Evidence]) -> SearchResponse:
    return SearchResponse(
        query="test",
        mode="balanced",
        answer="test",
        verification=None,
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
    report = AuditReport.from_response(response(evidence))
    assert report.independent_evidence_count == 2
    assert report.verified_evidence_count == 1
    assert report.failure_count == 0
    assert report.findings == ()


def test_audit_keeps_verdict_authority_explicitly_unadjudicated() -> None:
    report = AuditReport.from_response(response([]))
    assert report.verification == "not_adjudicated"


def test_audit_classifies_recoverable_and_terminal_failures() -> None:
    result = response([])
    result.failures = [
        Failure(type=FailureType.TIMEOUT, message="temporary timeout", recoverable=True),
        Failure(type=FailureType.API_ERROR, message="provider unavailable", recoverable=False),
    ]
    report = AuditReport.from_response(result)
    findings = {finding.code: finding for finding in report.findings}
    assert report.failure_count == 2
    assert findings["FAILURE_TIMEOUT"].severity is AuditSeverity.WARNING
    assert findings["FAILURE_API_ERROR"].severity is AuditSeverity.ERROR


def test_audit_evidence_handles_missing_evidence_and_failures() -> None:
    findings = audit_evidence(
        [],
        [Failure(type=FailureType.RATE_LIMIT, message="retry later", recoverable=True)],
    )
    by_code = {finding.code: finding for finding in findings}
    assert by_code["NO_EVIDENCE"].severity is AuditSeverity.ERROR
    assert by_code["NO_VERIFIED_EVIDENCE"].severity is AuditSeverity.WARNING
    assert by_code["FAILURE_RATE_LIMIT"].severity is AuditSeverity.WARNING
