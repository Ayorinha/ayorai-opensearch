"""Local append-only audit trace persistence for R2.

The store persists audit metadata and a content-addressed replay digest. It does
not persist raw prompts, evidence excerpts, credentials, or model outputs.
SQLite schema changes are versioned with PRAGMA user_version.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Final, Literal

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import AuditTraceResponse, SearchResponse
from ayorai_attractor.replay import ReplayBundle

_SCHEMA_VERSION = 2
_R2_V1: Final = "r2-v1"
_R2_V2: Final = "r2-v2"
ReplayVersion = Literal["r2-v1", "r2-v2"]
ReplayIntegrity = Literal["valid", "invalid"]


class AuditTraceStore:
    def __init__(self, path: str | None = None) -> None:
        configured: str = (
            path
            if path is not None
            else os.getenv("ATTRACTOR_AUDIT_DB", ".attractor/audit.sqlite3")
        )
        self.path = configured
        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._migrate()

    def __enter__(self) -> AuditTraceStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
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
        connection = self._connection
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'audit_traces'"
        ).fetchone()
        if exists is None:
            self._create_schema_v2(connection)
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            connection.commit()
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
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            connection.commit()
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

    def record(self, response: SearchResponse, report: AuditReport) -> str:
        events = [
            {
                "event": "audit.completed",
                "verification": "not_adjudicated",
                "evidence_count": report.evidence_count,
                "failure_count": report.failure_count,
            }
        ]
        replay = ReplayBundle.build(response.trace_id, events, version=_R2_V2)
        self._connection.execute(
            """
            INSERT OR REPLACE INTO audit_traces (
                trace_id, legacy_verification, verification, operation_status,
                evidence_count, independent_evidence_count,
                verified_evidence_count, failure_count, finding_count,
                replay_digest, replay_version, schema_version
            ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.trace_id,
                response.operation_status,
                report.evidence_count,
                report.independent_evidence_count,
                report.verified_evidence_count,
                report.failure_count,
                len(report.findings),
                replay.digest,
                _R2_V2,
                _SCHEMA_VERSION,
            ),
        )
        self._connection.commit()
        return replay.digest

    def verify(self, trace_id: str) -> ReplayIntegrity:
        row = self._connection.execute(
            """
            SELECT legacy_verification, evidence_count, failure_count,
                   replay_digest, replay_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown audit trace: {trace_id}")
        legacy_verification, evidence_count, failure_count, stored_digest, version = row
        if version not in (_R2_V1, _R2_V2):
            return "invalid"
        verification = legacy_verification if version == _R2_V1 else "not_adjudicated"
        if verification is None:
            return "invalid"
        events: list[dict[str, Any]] = [
            {
                "event": "audit.completed",
                "verification": verification,
                "evidence_count": int(evidence_count),
                "failure_count": int(failure_count),
            }
        ]
        rebuilt = ReplayBundle.build(
            trace_id,
            events,
            version=version,
        )
        return "valid" if rebuilt.digest == stored_digest else "invalid"

    def get(self, trace_id: str) -> AuditTraceResponse | None:
        row = self._connection.execute(
            """
            SELECT trace_id, operation_status, evidence_count,
                   independent_evidence_count, verified_evidence_count,
                   failure_count, finding_count, replay_digest,
                   legacy_verification, replay_version
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
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
