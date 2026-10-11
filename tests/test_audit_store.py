import sqlite3

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import SearchResponse
from ayorai_attractor.replay import ReplayBundle


def test_audit_trace_store_persists_summary_and_digest(tmp_path) -> None:
    response = SearchResponse(
        query="test query",
        mode="balanced",
        answer="test",
        verification=None,
        confidence=None,
        operation_status="completed",
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
    assert saved.operation_status == "completed"
    assert saved.replay_digest == digest

    with sqlite3.connect(tmp_path / "audit.sqlite3") as connection:
        stored = connection.execute(
            """
            SELECT verification, legacy_verification, operation_status,
                   replay_version, schema_version
            FROM audit_traces WHERE trace_id = ?
            """,
            ("tr_persisted",),
        ).fetchone()
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
    assert stored == (None, None, "completed", "r2-v2", 2)
    assert ReplayBundle.build(
        "tr_persisted",
        [
            {
                "event": "audit.completed",
                "verification": "not_adjudicated",
                "evidence_count": 0,
                "failure_count": 0,
            }
        ],
        version="r2-v2",
    ).digest == digest


def test_schema_v1_migration_preserves_legacy_value_and_digest(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    trace_id = "tr_legacy"
    events = [
        {
            "event": "audit.completed",
            "verification": "supported",
            "evidence_count": 3,
            "failure_count": 1,
        }
    ]
    legacy_digest = ReplayBundle.build(trace_id, events, version="r2-v1").digest

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE audit_traces (
                trace_id TEXT PRIMARY KEY,
                verification TEXT NOT NULL,
                evidence_count INTEGER NOT NULL,
                independent_evidence_count INTEGER NOT NULL,
                verified_evidence_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                finding_count INTEGER NOT NULL,
                replay_digest TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO audit_traces VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (trace_id, "supported", 3, 2, 1, 1, 2, legacy_digest),
        )

    first = AuditTraceStore(str(path))
    with sqlite3.connect(path) as connection:
        migrated = connection.execute(
            """
            SELECT legacy_verification, verification, operation_status,
                   replay_digest, replay_version, schema_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
    assert migrated == ("supported", None, "not_recorded", legacy_digest, "r2-v1", 2)
    assert first.get(trace_id) is not None
    assert first.get(trace_id).operation_status == "not_recorded"

    # Reopening an already migrated database must be idempotent.
    AuditTraceStore(str(path))
    with sqlite3.connect(path) as connection:
        migrated_again = connection.execute(
            """
            SELECT legacy_verification, verification, operation_status,
                   replay_digest, replay_version, schema_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
    assert migrated_again == migrated


def test_migration_recognizes_existing_r2_v2_rows(tmp_path) -> None:
    path = tmp_path / "r2-v2.sqlite3"
    trace_id = "tr_r2_v2"
    events = [
        {
            "event": "audit.completed",
            "verification": "not_adjudicated",
            "evidence_count": 1,
            "failure_count": 0,
        }
    ]
    digest = ReplayBundle.build(trace_id, events, version="r2-v2").digest

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE audit_traces (
                trace_id TEXT PRIMARY KEY,
                verification TEXT NOT NULL,
                evidence_count INTEGER NOT NULL,
                independent_evidence_count INTEGER NOT NULL,
                verified_evidence_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                finding_count INTEGER NOT NULL,
                replay_digest TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO audit_traces VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (trace_id, "not_adjudicated", 1, 1, 0, 0, 0, digest),
        )

    AuditTraceStore(str(path))
    with sqlite3.connect(path) as connection:
        migrated = connection.execute(
            """
            SELECT legacy_verification, verification, operation_status,
                   replay_digest, replay_version, schema_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
    assert migrated == (None, None, "not_recorded", digest, "r2-v2", 2)


def test_missing_trace_returns_none(tmp_path) -> None:
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    assert store.get("missing") is None
