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

import hashlib
import hmac
import os
import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Final, Literal

from ayorai_attractor import __version__
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
    "recorded_at",
    "software_version",
)
ReplayIntegrity = Literal["valid", "invalid"]


def _r2_v3_events(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Canonical replay events for an r2-v3 trace (one source for record and verify)."""
    return [{"event": "audit.completed", **{name: fields[name] for name in _R2_V3_FIELDS}}]


def _utc_timestamp(moment: datetime) -> str:
    """Fixed-width UTC ISO 8601 with microseconds, so text order equals time order."""
    if moment.tzinfo is None:
        raise ValueError("audit timestamps must be timezone-aware")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


_KEY_ID = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
_MIN_MAC_KEY_BYTES = 32


def audit_mac_keys_from_env() -> tuple[tuple[str, bytes], ...]:
    """Parse ATTRACTOR_AUDIT_HMAC_KEYS="id:hex[,id:hex...]" (first = active).

    The keys live outside the database, so a writer of the SQLite file alone
    cannot forge a trace. Empty or unset disables MACs.
    """
    raw = os.getenv("ATTRACTOR_AUDIT_HMAC_KEYS", "").strip()
    if not raw:
        return ()
    keys: list[tuple[str, bytes]] = []
    for item in raw.split(","):
        key_id, separator, hex_key = item.strip().partition(":")
        if not separator:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS entries must be id:hex")
        if not _KEY_ID.match(key_id) or any(key_id == seen for seen, _ in keys):
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS needs unique ids of [A-Za-z0-9_.-]{1,32}")
        try:
            key = bytes.fromhex(hex_key)
        except ValueError as exc:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS keys must be hex") from exc
        if len(key) < _MIN_MAC_KEY_BYTES:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS keys must have at least 32 bytes")
        keys.append((key_id, key))
    return tuple(keys)


def _mac(key: bytes, version: str, digest: str) -> str:
    return hmac.new(key, f"{version}:{digest}".encode("ascii"), hashlib.sha256).hexdigest()


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
    def __init__(
        self,
        path: str | None = None,
        clock: Callable[[], datetime] | None = None,
        mac_keys: tuple[tuple[str, bytes], ...] | None = None,
    ) -> None:
        configured: str = (
            path
            if path is not None
            else os.getenv("ATTRACTOR_AUDIT_DB", ".attractor/audit.sqlite3")
        )
        self.path = configured
        self._clock = clock or (lambda: datetime.now(UTC))
        self._mac_keys = audit_mac_keys_from_env() if mac_keys is None else mac_keys
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
        """Schema v3: who (owner), when (recorded_at, UTC) and which software version.

        The three columns are NULL on traces recorded before schema v3.
        """
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(audit_traces)").fetchall()
        }
        for column in ("owner", "recorded_at", "software_version", "replay_mac", "mac_key_id"):
            if column not in columns:
                # Column names are internal constants, never caller input.
                connection.execute(f"ALTER TABLE audit_traces ADD COLUMN {column} TEXT")
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
            "recorded_at": _utc_timestamp(self._clock()),
            "software_version": __version__,
        }
        replay = ReplayBundle.build(report.trace_id, _r2_v3_events(fields), version=_R2_V3)
        mac_key_id, replay_mac = None, None
        if self._mac_keys:
            mac_key_id, key = self._mac_keys[0]
            replay_mac = _mac(key, _R2_V3, replay.digest)
        try:
            self._connection.execute(
                """
                INSERT INTO audit_traces (
                    trace_id, legacy_verification, verification, operation_status,
                    evidence_count, independent_evidence_count,
                    verified_evidence_count, failure_count, finding_count,
                    replay_digest, replay_version, schema_version, owner,
                    recorded_at, software_version, replay_mac, mac_key_id
                ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    fields["recorded_at"],
                    fields["software_version"],
                    replay_mac,
                    mac_key_id,
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

    def backup(self, destination: str) -> int:
        """Write a consistent online copy of the store to a new file.

        Uses SQLite's backup API, so it is safe while this process keeps writing
        (writes wait for the copy). Refuses to overwrite an existing file and
        checks the copy with PRAGMA integrity_check. Returns the number of traces.
        """
        target = Path(destination)
        if target.exists():
            raise FileExistsError(f"backup destination already exists: {destination}")
        target.parent.mkdir(parents=True, exist_ok=True)
        copy = sqlite3.connect(str(target))
        try:
            with self._lock:
                self._connection.backup(copy)
            if copy.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise sqlite3.DatabaseError(f"backup failed integrity_check: {destination}")
            return int(copy.execute("SELECT COUNT(*) FROM audit_traces").fetchone()[0])
        finally:
            copy.close()

    def purge_recorded_before(self, cutoff: datetime) -> int:
        """Delete traces recorded before ``cutoff`` (retention); returns how many.

        Traces without recorded_at (recorded before schema v3) are never purged
        here: their age is unknown.
        """
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM audit_traces WHERE recorded_at IS NOT NULL AND recorded_at < ?",
                (_utc_timestamp(cutoff),),
            )
            self._connection.commit()
            return int(cursor.rowcount)

    def verify_all(self) -> dict[str, int]:
        """Replay-verify every stored trace (for example after a restore)."""
        with self._lock:
            trace_ids = [
                str(row[0])
                for row in self._connection.execute(
                    "SELECT trace_id FROM audit_traces ORDER BY trace_id"
                ).fetchall()
            ]
            counts = {"valid": 0, "invalid": 0}
            for trace_id in trace_ids:
                counts[self._verify_locked(trace_id)] += 1
            return counts

    def verify(self, trace_id: str) -> ReplayIntegrity:
        with self._lock:
            return self._verify_locked(trace_id)

    def _verify_locked(self, trace_id: str) -> ReplayIntegrity:
        row = self._connection.execute(
            """
            SELECT legacy_verification, verification, operation_status, evidence_count,
                   independent_evidence_count, verified_evidence_count, failure_count,
                   finding_count, schema_version, owner, recorded_at, software_version,
                   replay_digest, replay_version, replay_mac, mac_key_id
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown audit trace: {trace_id}")
        fields = dict(zip(_R2_V3_FIELDS, row[:12], strict=True))
        stored_digest, version, stored_mac, mac_key_id = row[12], row[13], row[14], row[15]
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
        if rebuilt.digest != stored_digest:
            return "invalid"
        has_mac_metadata = stored_mac is not None or mac_key_id is not None
        if self._mac_keys:
            # When keyed integrity is enabled, every replay version must carry a
            # valid MAC. This also prevents downgrading an r2-v3 trace to a legacy
            # replay version to bypass keyed verification.
            key = dict(self._mac_keys).get(str(mac_key_id)) if mac_key_id is not None else None
            if key is None or stored_mac is None:
                return "invalid"
            if not hmac.compare_digest(_mac(key, str(version), stored_digest), str(stored_mac)):
                return "invalid"
        elif has_mac_metadata:
            # Never silently downgrade a previously keyed trace to digest-only
            # verification when the verification keys are missing.
            return "invalid"
        return "valid"

    def seal_unsealed(self) -> int:
        """MAC valid unsealed r2-v1, r2-v2 and r2-v3 traces; return how many.

        Only traces whose replay digest is still valid are sealed, with the active
        key. Run once when enabling ATTRACTOR_AUDIT_HMAC_KEYS on an existing store.
        """
        if not self._mac_keys:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS is not configured")
        key_id, key = self._mac_keys[0]
        sealed = 0
        with self._lock:
            rows = self._connection.execute(
                "SELECT trace_id, replay_digest, replay_version FROM audit_traces "
                "WHERE replay_version IN (?, ?, ?) AND replay_mac IS NULL "
                "AND mac_key_id IS NULL ORDER BY trace_id",
                (_R2_V1, _R2_V2, _R2_V3),
            ).fetchall()
            saved_keys, self._mac_keys = self._mac_keys, ()
            try:
                valid = [row for row in rows if self._verify_locked(str(row[0])) == "valid"]
            finally:
                self._mac_keys = saved_keys
            for trace_id, digest, version in valid:
                self._connection.execute(
                    "UPDATE audit_traces SET replay_mac = ?, mac_key_id = ? WHERE trace_id = ?",
                    (_mac(key, str(version), str(digest)), key_id, trace_id),
                )
                sealed += 1
            self._connection.commit()
        return sealed

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
