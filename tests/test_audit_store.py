from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import SearchResponse


def test_audit_trace_store_persists_summary_and_digest(tmp_path) -> None:
    response = SearchResponse(
        query="test query",
        mode="balanced",
        answer="test",
        verification=None,
        confidence=0.0,
        trace_id="tr_persisted",
    )
    report = AuditReport.from_response(response)
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))

    digest = store.record(response, report)

    reopened = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    saved = reopened.get("tr_persisted")

    assert saved is not None
    assert saved.trace_id == "tr_persisted"
    assert saved.verification is None
    assert saved.verdict_authority == "not_adjudicated"
    assert saved.formal_verification_endpoint == "/v1/verify"
    assert saved.replay_digest == digest


def test_missing_trace_returns_none(tmp_path) -> None:
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    assert store.get("missing") is None
