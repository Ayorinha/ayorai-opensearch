"""Local audit trace persistence for R2.

The normal store API appends records and rejects reuse of an existing trace_id.
Replay digests can detect changes to the fields covered by replay verification,
but this SQLite store is not tamper-proof against direct database edits or an
administrator with write access. It does not persist raw prompts, evidence
excerpts, credentials, or model outputs. SQLite schema changes are versioned
with PRAGMA user_version. Access to the shared connection is serialized within this
process; this does not make the store a multi-process or multi-replica database.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Final, Literal

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import AuditTraceResponse, SearchResponse
from ayorai_attractor.replay import ReplayBundle

_SCHEMA_VERSION = 3
_R2_V1: Final = "r2-v1"
_R2_V2: Final = "r2-v2"
_R2_V3: Final = "r2-v3"
ReplayVersion = Literal["r2-v1", "r2-v2", "r2-v3"]
# Columns bound by an r2-v3 digest: every persisted field of a trace. r2-v1 and
# r2-v2 digests bind only verification, evidence_count and failure_count; they
# are still verified as written, but new traces are recorded as r2-v3.
_R2_V3_FIELDS: Final = (
    "legacy_verification",
    "verification",
    "operation_status",
    "evidence_count",
    "independent_evidence_count",
    "verified_evidence_count",
    "failure_count",
    "finding_count",
    "schema_version",
    "owner",
)
ReplayIntegrity = Literal["valid", "invalid"]


def _r2_v3_events(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Canonical replay events for an r2-v3 trace (one source for record and verify)."""
    return [{"event": "audit.completed", **{name: fields[name] for name in _R2_V3_FIELDS}}]


LEGACY_TRACE_POLICIES = ("hidden", "shared")


def legacy_trace_policy_from_env() -> str:
    """ATTRACTOR_AUDIT_LEGACY_TRACES: who may read traces recorded without an owner.

    "hidden" (default): no authenticated key reads them, because their creator is
    unknown and any key could belong to another client. "shared": every
    authenticated key reads them (the behaviour before owners were recorded).
    """
    policy = os.getenv("ATTRACTOR_AUDIT_LEGACY_TRACES", "hidden").strip().lower()
    if policy not in LEGACY_TRACE_POLICIES:
        raise ValueError("ATTRACTOR_AUDIT_LEGACY_TRACES must be 'hidden' or 'shared'")
    return policy


class DuplicateAuditTraceError(ValueError):
    """Raised when an audit trace ID has already been recorded."""


class AuditTraceStore:
    def __init__(self, path: str | None = None) -> None:
        configured: str = (
            path
            if path is not None
            else os.getenv("ATTRACTOR_AUDIT_DB", ".attractor/audit.sqlite3")
        )
        self.path = configured
        self._lock = RLock()
        self._legacy_policy = legacy_trace_policy_from_env()
        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        try:
            self._migrate()
        except BaseException:
            # A failed migration must not leak the connection; the rollback in
            # _migrate_locked already left the database as it was.
            self._connection.close()
            raise

    def __enter__(self) -> AuditTraceStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema_v2(self, connection: sqlite3.Connection) -> None:
        self._create_schema_v2_named(connection, "audit_traces")

    @staticmethod
    def _create_schema_v2_named(connection: sqlite3.Connection, table_name: str) -> None:
        # The table name is an internal constant, never caller input.
        connection.execute(
            f"""
            CREATE TABLE {table_name} (
                trace_id TEXT PRIMARY KEY,
                legacy_verification TEXT,
                verification TEXT,
                operation_status TEXT NOT NULL,
                evidence_count INTEGER NOT NULL,
                independent_evidence_count INTEGER NOT NULL,
                verified_evidence_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                finding_count INTEGER NOT NULL,
                replay_digest TEXT NOT NULL,
                replay_version TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            )
            """
        )

    def _migrate(self) -> None:
        with self._lock:
            try:
                self._migrate_locked()
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def _migrate_locked(self) -> None:
        connection = self._connection
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'audit_traces'"
        ).fetchone()
        if exists is None:
            self._create_schema_v2(connection)
            self._finish_migration(connection)
            return

        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(audit_traces)").fetchall()
        }
        required = {
            "legacy_verification",
            "verification",
            "operation_status",
            "replay_version",
            "schema_version",
        }
        if required.issubset(columns):
            self._finish_migration(connection)
            return

        rows = connection.execute(
            """
            SELECT trace_id, verification, evidence_count,
                   independent_evidence_count, verified_evidence_count,
                   failure_count, finding_count, replay_digest
            FROM audit_traces ORDER BY trace_id
            """
        ).fetchall()
        connection.execute("BEGIN")
        connection.execute("DROP TABLE IF EXISTS audit_traces_v2")
        self._create_schema_v2_named(connection, "audit_traces_v2")
        for row in rows:
            (
                trace_id,
                old_verification,
                evidence_count,
                independent_count,
                verified_count,
                failure_count,
                finding_count,
                replay_digest,
            ) = row
            version = self._detect_replay_version(
                str(trace_id),
                str(old_verification),
                int(evidence_count),
                int(failure_count),
                str(replay_digest),
            )
            is_current_contract = version == _R2_V2
            connection.execute(
                """
                INSERT INTO audit_traces_v2 (
                    trace_id, legacy_verification, verification, operation_status,
                    evidence_count, independent_evidence_count,
                    verified_evidence_count, failure_count, finding_count,
                    replay_digest, replay_version, schema_version
                ) VALUES (?, ?, NULL, 'not_recorded', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    None if is_current_contract else old_verification,
                    evidence_count,
                    independent_count,
                    verified_count,
                    failure_count,
                    finding_count,
                    replay_digest,
                    version,
                    _SCHEMA_VERSION,
                ),
            )
        connection.execute("DROP TABLE audit_traces")
        connection.execute("ALTER TABLE audit_traces_v2 RENAME TO audit_traces")
        self._finish_migration(connection)

    @staticmethod
    def _finish_migration(connection: sqlite3.Connection) -> None:
        """Schema v3: traces record the principal that created them (NULL = legacy)."""
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(audit_traces)").fetchall()
        }
        if "owner" not in columns:
            connection.execute("ALTER TABLE audit_traces ADD COLUMN owner TEXT")
        connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        connection.commit()

    @staticmethod
    def _detect_replay_version(
        trace_id: str,
        old_verification: str,
        evidence_count: int,
        failure_count: int,
        replay_digest: str,
    ) -> ReplayVersion:
        if old_verification == "not_adjudicated":
            events: list[dict[str, Any]] = [
                {
                    "event": "audit.completed",
                    "verification": "not_adjudicated",
                    "evidence_count": evidence_count,
                    "failure_count": failure_count,
                }
            ]
            candidate = ReplayBundle.build(trace_id, events, version=_R2_V2)
            if candidate.digest == replay_digest:
                return _R2_V2
        return _R2_V1

    def record(
        self, response: SearchResponse, report: AuditReport, owner: str | None = None
    ) -> str:
        with self._lock:
            return self._record_locked(response, report, owner)

    def _record_locked(
        self, response: SearchResponse, report: AuditReport, owner: str | None
    ) -> str:
        fields: dict[str, Any] = {
            "legacy_verification": None,
            "verification": None,
            "operation_status": response.operation_status,
            "evidence_count": report.evidence_count,
            "independent_evidence_count": report.independent_evidence_count,
            "verified_evidence_count": report.verified_evidence_count,
            "failure_count": report.failure_count,
            "finding_count": len(report.findings),
            "schema_version": _SCHEMA_VERSION,
            "owner": owner,
        }
        replay = ReplayBundle.build(report.trace_id, _r2_v3_events(fields), version=_R2_V3)
        try:
            self._connection.execute(
                """
                INSERT INTO audit_traces (
                    trace_id, legacy_verification, verification, operation_status,
                    evidence_count, independent_evidence_count,
                    verified_evidence_count, failure_count, finding_count,
                    replay_digest, replay_version, schema_version, owner
                ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.trace_id,
                    fields["operation_status"],
                    fields["evidence_count"],
                    fields["independent_evidence_count"],
                    fields["verified_evidence_count"],
                    fields["failure_count"],
                    fields["finding_count"],
                    replay.digest,
                    _R2_V3,
                    fields["schema_version"],
                    owner,
                ),
            )
        except sqlite3.IntegrityError as exc:
            if "audit_traces.trace_id" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise DuplicateAuditTraceError(
                    f"Audit trace already exists: {report.trace_id}"
                ) from exc
            raise
        self._connection.commit()
        return replay.digest

    def verify(self, trace_id: str) -> ReplayIntegrity:
        with self._lock:
            return self._verify_locked(trace_id)

    def _verify_locked(self, trace_id: str) -> ReplayIntegrity:
        row = self._connection.execute(
            """
            SELECT legacy_verification, verification, operation_status, evidence_count,
                   independent_evidence_count, verified_evidence_count, failure_count,
                   finding_count, schema_version, owner, replay_digest, replay_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown audit trace: {trace_id}")
        fields = dict(zip(_R2_V3_FIELDS, row[:10], strict=True))
        stored_digest, version = row[10], row[11]
        if version == _R2_V3:
            events = _r2_v3_events(fields)
        elif version in (_R2_V1, _R2_V2):
            verification = fields["legacy_verification"] if version == _R2_V1 else "not_adjudicated"
            if verification is None:
                return "invalid"
            events = [
                {
                    "event": "audit.completed",
                    "verification": verification,
                    "evidence_count": int(fields["evidence_count"]),
                    "failure_count": int(fields["failure_count"]),
                }
            ]
        else:
            return "invalid"
        rebuilt = ReplayBundle.build(trace_id, events, version=version)
        return "valid" if rebuilt.digest == stored_digest else "invalid"

    def get(self, trace_id: str, requester: str | None = None) -> AuditTraceResponse | None:
        """Return the trace only to its owner.

        ``requester`` is the authenticated principal, or None when authentication
        is off (single tenant: only traces without an owner exist to read). Traces
        without an owner are returned to authenticated principals only under the
        "shared" legacy policy. A trace the requester may not read is reported as
        missing (None), so the lookup does not reveal that it exists.
        """
        with self._lock:
            return self._get_locked(trace_id, requester)

    def _get_locked(self, trace_id: str, requester: str | None) -> AuditTraceResponse | None:
        row = self._connection.execute(
            """
            SELECT trace_id, operation_status, evidence_count,
                   independent_evidence_count, verified_evidence_count,
                   failure_count, finding_count, replay_digest,
                   legacy_verification, replay_version
            FROM audit_traces WHERE trace_id = ? AND (
                (owner IS NULL AND (? IS NULL OR ? = 'shared')) OR owner = ?
            )
            """,
            (trace_id, requester, self._legacy_policy, requester),
        ).fetchone()
        if row is None:
            return None
        return AuditTraceResponse(
            trace_id=str(row[0]),
            verification=None,
            verdict_authority="not_adjudicated",
            formal_verification_endpoint="/v1/verify",
            operation_status=row[1],
            evidence_count=int(row[2]),
            independent_evidence_count=int(row[3]),
            verified_evidence_count=int(row[4]),
            failure_count=int(row[5]),
            finding_count=int(row[6]),
            replay_digest=str(row[7]),
            legacy_verification=row[8],
            replay_version=row[9],
            replay_integrity=self.verify(trace_id),
        )
