"""Local append-only audit trace persistence for R2.

The store persists audit metadata and a content-addressed replay digest. It does
not persist raw prompts, evidence excerpts, credentials, or model outputs.
SQLite is used so the same process can inspect a trace after the request ends.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import AuditTraceResponse, SearchResponse
from ayorai_attractor.replay import ReplayBundle


class AuditTraceStore:
    def __init__(self, path: str | None = None) -> None:
        configured: str = path if path is not None else os.getenv(
            "ATTRACTOR_AUDIT_DB", ".attractor/audit.sqlite3"
        )
        self.path = configured
        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        connection = self._connection
        connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_traces (
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

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(self, response: SearchResponse, report: AuditReport) -> str:
        events = [
            {
                "event": "audit.completed",
                "verification": report.verification,
                "evidence_count": report.evidence_count,
                "failure_count": report.failure_count,
            }
        ]
        replay = ReplayBundle.build(response.trace_id, events, version="r2-v1")
        connection = self._connection
        connection.execute(
            """
            INSERT OR REPLACE INTO audit_traces
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.trace_id,
                report.verification,
                report.evidence_count,
                report.independent_evidence_count,
                report.verified_evidence_count,
                report.failure_count,
                len(report.findings),
                replay.digest,
            ),
        )
        return replay.digest

    def get(self, trace_id: str) -> AuditTraceResponse | None:
        connection = self._connection
        row = connection.execute(
            """
            SELECT trace_id, verification, evidence_count,
                   independent_evidence_count, verified_evidence_count,
                   failure_count, finding_count, replay_digest
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            return None
        return AuditTraceResponse(
            trace_id=str(row[0]),
            verification=str(row[1]),
            evidence_count=int(row[2]),
            independent_evidence_count=int(row[3]),
            verified_evidence_count=int(row[4]),
            failure_count=int(row[5]),
            finding_count=int(row[6]),
            replay_digest=str(row[7]),
        )
