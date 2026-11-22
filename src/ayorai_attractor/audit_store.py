"""Local audit trace persistence for R2.

The normal store API appends records and rejects reuse of an existing trace_id.
Replay digests can detect changes to the fields covered by replay verification,
but this SQLite store is not tamper-proof against direct database edits or an
administrator with write access. It does not persist raw prompts, evidence
excerpts, credentials, or model outputs. SQLite schema changes are versioned
with PRAGMA user_version. Access to the shared connection is serialized within this
process; this does not make the store a multi-process or multi-replica database.

Every trace recorded through this API is also appended to ``audit_chain``, a
sequence of links chained by HMAC (SHA-256 without keys). ``verify_chain()``
detects a trace deleted from the middle, a chain entry removed or rewritten, a
trace inserted without the API, and, against a checkpoint kept outside the
host, truncation of the most recent entries or a rollback to an older copy.
Retention purges are recorded in the chain, so they are not reported as
deletions. Without an external checkpoint, removing the newest entries, or
replacing the whole database by an older one, cannot be detected locally.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
from collections.abc import Callable, Collection, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any, Final, Literal

from ayorai_attractor import __version__
from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import AuditTraceResponse, SearchResponse
from ayorai_attractor.replay import ReplayBundle

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 4
_R2_V1: Final = "r2-v1"
_R2_V2: Final = "r2-v2"
_R2_V3: Final = "r2-v3"
_R2_V4: Final = "r2-v4"
ReplayVersion = Literal["r2-v1", "r2-v2", "r2-v3", "r2-v4"]
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
# r2-v4 (schema 4) adds the adjudication a trace was recorded with (POST /v2/audit):
# the claim-check digest and the SHA-256 of the canonical adjudication result. Its
# digest, and therefore its HMAC, binds every r2-v3 field plus these two.
_ADJUDICATION_FIELDS: Final = ("check_trace_id", "adjudication_sha256")
_R2_V4_FIELDS: Final = _R2_V3_FIELDS + _ADJUDICATION_FIELDS
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
ReplayIntegrity = Literal["valid", "invalid"]


def _r2_v3_events(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Canonical replay events for an r2-v3 trace (one source for record and verify)."""
    return [{"event": "audit.completed", **{name: fields[name] for name in _R2_V3_FIELDS}}]


def _r2_v4_events(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Canonical replay events for an r2-v4 trace: r2-v3 plus the bound adjudication."""
    return [{"event": "audit.completed", **{name: fields[name] for name in _R2_V4_FIELDS}}]


def _utc_timestamp(moment: datetime) -> str:
    """Fixed-width UTC ISO 8601 with microseconds, so text order equals time order."""
    if moment.tzinfo is None:
        raise ValueError("audit timestamps must be timezone-aware")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


_KEY_ID = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
_MIN_MAC_KEY_BYTES = 32


def _validate_mac_keys(
    keys: tuple[tuple[str, bytes], ...],
) -> tuple[tuple[str, bytes], ...]:
    """Apply the same key policy to environment and explicitly injected keys."""
    if not isinstance(keys, tuple):
        raise ValueError("HMAC keys must be a tuple of (key_id, key_bytes) pairs")
    validated: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for item in keys:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError("HMAC keys must be (key_id, key_bytes) pairs")
        key_id, key = item
        if not isinstance(key_id, str) or _KEY_ID.fullmatch(key_id) is None or key_id in seen:
            raise ValueError("HMAC keys need unique ids of [A-Za-z0-9_.-]{1,32}")
        if not isinstance(key, bytes) or len(key) < _MIN_MAC_KEY_BYTES:
            raise ValueError("HMAC keys must have at least 32 bytes")
        seen.add(key_id)
        validated.append((key_id, key))
    return tuple(validated)


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
    return _validate_mac_keys(tuple(keys))


def audit_hmac_required_from_env() -> bool:
    """Whether deployment policy requires keyed audit integrity at startup.

    ATTRACTOR_AUDIT_HMAC_REQUIRED defaults to false for backwards-compatible
    local development. Production deployments should set it to true and provide
    ATTRACTOR_AUDIT_HMAC_KEYS through a secret manager or equivalent.
    """
    raw = os.getenv("ATTRACTOR_AUDIT_HMAC_REQUIRED", "false").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False
    raise ValueError(
        "ATTRACTOR_AUDIT_HMAC_REQUIRED must be a boolean (true/false, 1/0, yes/no, on/off)"
    )


def _mac(key: bytes, version: str, digest: str) -> str:
    return hmac.new(key, f"{version}:{digest}".encode("ascii"), hashlib.sha256).hexdigest()


def _mac_for_trace(key: bytes, version: str, digest: str, fields: dict[str, Any]) -> str:
    """Authenticate the full persisted row when a legacy digest omits columns.

    r2-v1 and r2-v2 intentionally retain their historical digest contracts.
    Their HMAC must therefore bind the schema-v3 fields that those digests do
    not cover (notably owner and recorded_at). r2-v3 already binds every field.
    """
    if version in (_R2_V3, _R2_V4):
        return _mac(key, version, digest)
    payload = {
        "domain": "ayorai.audit.legacy-row.v1",
        "replay_version": version,
        "replay_digest": digest,
        "fields": {name: fields[name] for name in _R2_V3_FIELDS},
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


_CHAIN_DOMAIN: Final = "ayorai.audit.chain.v1"
_CHAIN_GENESIS: Final = "genesis"
ChainKind = Literal["trace", "purge"]


def _chain_link(
    key: bytes | None,
    *,
    seq: int,
    kind: str,
    trace_id: str | None,
    replay_digest: str | None,
    payload: str | None,
    previous: str,
) -> str:
    """Link of one chain entry: HMAC-SHA256 with a key, SHA-256 without one."""
    canonical = json.dumps(
        {
            "domain": _CHAIN_DOMAIN,
            "seq": seq,
            "kind": kind,
            "trace_id": trace_id,
            "replay_digest": replay_digest,
            "payload": payload,
            "previous": previous,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if key is None:
        return hashlib.sha256(canonical).hexdigest()
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def _seq_ranges(seqs: list[int]) -> list[list[int]]:
    """Compress sorted sequence numbers into inclusive [first, last] ranges."""
    ranges: list[list[int]] = []
    for seq in sorted(seqs):
        if ranges and seq == ranges[-1][1] + 1:
            ranges[-1][1] = seq
        else:
            ranges.append([seq, seq])
    return ranges


LEGACY_TRACE_POLICIES = ("hidden", "shared")


_RETENTION_MAX_DAYS: Final = 36_500
# The automatic purge runs at startup and then at most once per interval, on the
# write path, so a busy service does not delete on every request.
_RETENTION_INTERVAL: Final = timedelta(hours=1)


def audit_retention_days_from_env() -> int | None:
    """Read ATTRACTOR_AUDIT_RETENTION_DAYS; unset or empty disables automatic purge.

    The retention period and its legal basis are the data controller's decision,
    so nothing is deleted unless the operator sets a positive number of days.
    """
    raw = os.getenv("ATTRACTOR_AUDIT_RETENTION_DAYS", "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError as exc:
        raise ValueError("ATTRACTOR_AUDIT_RETENTION_DAYS must be a whole number of days") from exc
    if not 1 <= days <= _RETENTION_MAX_DAYS:
        raise ValueError(
            f"ATTRACTOR_AUDIT_RETENTION_DAYS must be between 1 and {_RETENTION_MAX_DAYS}"
        )
    return days


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
        self._mac_keys = (
            audit_mac_keys_from_env() if mac_keys is None else _validate_mac_keys(mac_keys)
        )
        self._hmac_required = audit_hmac_required_from_env()
        self._lock = RLock()
        self._legacy_policy = legacy_trace_policy_from_env()
        self._retention_days = audit_retention_days_from_env()
        self._last_retention_run: datetime | None = None
        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        try:
            self._migrate()
            self._require_hmac_keys_for_sealed_store()
            with self._lock:
                self._apply_retention_locked()
        except BaseException:
            # A failed migration or fail-closed configuration check must not
            # leak the connection; migration rollback leaves the database intact.
            self._connection.close()
            raise

    def _require_hmac_keys_for_sealed_store(self) -> None:
        """Refuse a silent HMAC downgrade when opening an already sealed store."""
        if self._hmac_required and not self._mac_keys:
            raise ValueError(
                "ATTRACTOR_AUDIT_HMAC_REQUIRED=true requires "
                "ATTRACTOR_AUDIT_HMAC_KEYS to be configured"
            )
        if self._mac_keys:
            return
        sealed = self._connection.execute(
            "SELECT 1 FROM audit_traces "
            "WHERE replay_mac IS NOT NULL OR mac_key_id IS NOT NULL LIMIT 1"
        ).fetchone()
        if sealed is not None:
            raise ValueError(
                "ATTRACTOR_AUDIT_HMAC_KEYS must be configured to open a store "
                "containing HMAC-sealed traces"
            )

    def __enter__(self) -> AuditTraceStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _rollback_open_transaction(self) -> None:
        """Undo a write left half done by an exception, so a later commit cannot keep it."""
        if self._connection.in_transaction:
            self._connection.rollback()

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

        The three columns are NULL on traces recorded before schema v3. Schema v4
        adds the adjudication columns (check_trace_id, adjudication_sha256), NULL on
        every trace that is not r2-v4.
        """
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(audit_traces)").fetchall()
        }
        for column in (
            "owner",
            "recorded_at",
            "software_version",
            "replay_mac",
            "mac_key_id",
            *_ADJUDICATION_FIELDS,
        ):
            if column not in columns:
                # Column names are internal constants, never caller input.
                connection.execute(f"ALTER TABLE audit_traces ADD COLUMN {column} TEXT")
        # Additive: the sequence chain lives in its own table, so trace rows, their
        # digests and their MACs keep the schema-4 contract.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_chain (
                seq INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                trace_id TEXT UNIQUE,
                replay_digest TEXT,
                payload TEXT,
                link TEXT NOT NULL,
                key_id TEXT
            )
            """
        )
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
        self,
        response: SearchResponse,
        report: AuditReport,
        owner: str | None = None,
        *,
        adjudication: tuple[str | None, str] | None = None,
    ) -> str:
        """Persist a trace; return its replay digest.

        ``adjudication`` is ``(check_trace_id, adjudication_sha256)`` for a run that
        adjudicated claims (POST /v2/audit); the trace is then r2-v4 and its digest and
        HMAC bind the adjudication. Without it the trace is r2-v3, as before.
        """
        if adjudication is not None:
            check_trace_id, adjudication_sha256 = adjudication
            if _SHA256_HEX.fullmatch(adjudication_sha256) is None:
                raise ValueError("adjudication_sha256 must be 64 lowercase hex characters")
            if check_trace_id is not None and not check_trace_id.strip():
                raise ValueError("check_trace_id must be non-empty when present")
        with self._lock:
            try:
                return self._record_locked(response, report, owner, adjudication)
            except BaseException:
                # The trace and its chain entry are written in one transaction:
                # if either fails, neither may be committed by a later call.
                self._rollback_open_transaction()
                raise

    def _record_locked(
        self,
        response: SearchResponse,
        report: AuditReport,
        owner: str | None,
        adjudication: tuple[str | None, str] | None = None,
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
        if adjudication is None:
            version, events = _R2_V3, _r2_v3_events(fields)
            fields["check_trace_id"] = fields["adjudication_sha256"] = None
        else:
            fields["check_trace_id"], fields["adjudication_sha256"] = adjudication
            version, events = _R2_V4, _r2_v4_events(fields)
        replay = ReplayBundle.build(report.trace_id, events, version=version)
        mac_key_id, replay_mac = None, None
        if self._mac_keys:
            mac_key_id, key = self._mac_keys[0]
            replay_mac = _mac(key, version, replay.digest)
        try:
            self._connection.execute(
                """
                INSERT INTO audit_traces (
                    trace_id, legacy_verification, verification, operation_status,
                    evidence_count, independent_evidence_count,
                    verified_evidence_count, failure_count, finding_count,
                    replay_digest, replay_version, schema_version, owner,
                    recorded_at, software_version, replay_mac, mac_key_id,
                    check_trace_id, adjudication_sha256
                ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    version,
                    fields["schema_version"],
                    owner,
                    fields["recorded_at"],
                    fields["software_version"],
                    replay_mac,
                    mac_key_id,
                    fields["check_trace_id"],
                    fields["adjudication_sha256"],
                ),
            )
        except sqlite3.IntegrityError as exc:
            if "audit_traces.trace_id" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise DuplicateAuditTraceError(
                    f"Audit trace already exists: {report.trace_id}"
                ) from exc
            raise
        self._append_chain_locked("trace", report.trace_id, replay.digest, None)
        self._connection.commit()
        # The trace is durable from here on. The automatic retention is housekeeping:
        # its failure must not turn a recorded trace into a reported failure, and a
        # partial purge is undone. It runs again on the next write after the interval.
        try:
            self._apply_retention_locked()
        except sqlite3.Error as exc:
            self._rollback_open_transaction()
            logger.warning(
                "audit retention failed after recording a trace (%s)", type(exc).__name__
            )
        return replay.digest

    @property
    def retention_days(self) -> int | None:
        """Configured automatic retention in days, or None when disabled."""
        return self._retention_days

    def _apply_retention_locked(self) -> int:
        """Purge traces older than the configured retention, at most once per interval."""
        if self._retention_days is None:
            return 0
        now = self._clock()
        if self._last_retention_run is not None and now - self._last_retention_run < (
            _RETENTION_INTERVAL
        ):
            return 0
        self._last_retention_run = now
        return self._purge_locked(now - timedelta(days=self._retention_days), "retention")

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
            try:
                return self._purge_locked(cutoff, "purge_recorded_before")
            except BaseException:
                self._rollback_open_transaction()
                raise

    def _purge_locked(self, cutoff: datetime, reason: str) -> int:
        """Delete traces recorded before ``cutoff`` and record the purge in the chain."""
        cutoff_text = _utc_timestamp(cutoff)
        purged_seqs = [
            int(row[0])
            for row in self._connection.execute(
                "SELECT c.seq FROM audit_chain c JOIN audit_traces t ON t.trace_id = c.trace_id "
                "WHERE c.kind = 'trace' AND t.recorded_at IS NOT NULL AND t.recorded_at < ?",
                (cutoff_text,),
            ).fetchall()
        ]
        cursor = self._connection.execute(
            "DELETE FROM audit_traces WHERE recorded_at IS NOT NULL AND recorded_at < ?",
            (cutoff_text,),
        )
        deleted = int(cursor.rowcount)
        if deleted:
            payload = json.dumps(
                {
                    "reason": reason,
                    "cutoff": cutoff_text,
                    "deleted": deleted,
                    "seqs": _seq_ranges(purged_seqs),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            self._append_chain_locked("purge", None, None, payload)
        self._connection.commit()
        return deleted

    def _append_chain_locked(
        self,
        kind: ChainKind,
        trace_id: str | None,
        replay_digest: str | None,
        payload: str | None,
    ) -> None:
        """Append one entry, linked to the previous one, inside the caller's transaction."""
        head = self._connection.execute(
            "SELECT seq, link FROM audit_chain ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        seq = 1 if head is None else int(head[0]) + 1
        previous = _CHAIN_GENESIS if head is None else str(head[1])
        key_id, key = self._mac_keys[0] if self._mac_keys else (None, None)
        link = _chain_link(
            key,
            seq=seq,
            kind=kind,
            trace_id=trace_id,
            replay_digest=replay_digest,
            payload=payload,
            previous=previous,
        )
        self._connection.execute(
            "INSERT INTO audit_chain (seq, kind, trace_id, replay_digest, payload, link, key_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (seq, kind, trace_id, replay_digest, payload, link, key_id),
        )

    def ping(self) -> bool:
        """True when the database answers and both tables exist (readiness probe)."""
        try:
            with self._lock:
                tables = {
                    str(row[0])
                    for row in self._connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' "
                        "AND name IN ('audit_traces', 'audit_chain')"
                    ).fetchall()
                }
        except sqlite3.Error:
            return False
        return tables == {"audit_traces", "audit_chain"}

    def checkpoint(self) -> dict[str, Any]:
        """Head of the chain, to be kept outside this host (detects truncation and rollback).

        Returns ``{"seq": n, "link": hex}``; ``{"seq": 0, "link": "genesis"}`` when empty.
        """
        with self._lock:
            head = self._connection.execute(
                "SELECT seq, link FROM audit_chain ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        if head is None:
            return {"seq": 0, "link": _CHAIN_GENESIS}
        return {"seq": int(head[0]), "link": str(head[1])}

    def verify_chain(self, checkpoint: dict[str, Any] | None = None) -> dict[str, Any]:
        """Verify the sequence chain against the stored traces.

        Reports, in counts: ``broken_links`` (an entry removed, reordered or rewritten,
        or signed by an unknown key), ``missing_traces`` (a recorded trace deleted
        without a recorded purge), ``digest_mismatches`` (a trace whose digest differs
        from the one chained), ``unsequenced_traces`` (traces with no chain entry:
        recorded before the chain existed, or inserted without the API) and
        ``checkpoint_mismatch`` (the given external checkpoint is not in the chain:
        truncation or rollback). ``intact`` is true when none of the first three and
        no checkpoint mismatch occurred; ``complete`` additionally requires zero
        unsequenced traces.
        """
        with self._lock:
            entries = self._connection.execute(
                "SELECT seq, kind, trace_id, replay_digest, payload, link, key_id "
                "FROM audit_chain ORDER BY seq"
            ).fetchall()
            stored = {
                str(row[0]): str(row[1])
                for row in self._connection.execute(
                    "SELECT trace_id, replay_digest FROM audit_traces"
                ).fetchall()
            }
        keys = dict(self._mac_keys)
        broken = 0
        previous = _CHAIN_GENESIS
        expected_seq = 1
        purged: set[int] = set()
        chained_traces: dict[int, tuple[str, str]] = {}
        links: dict[int, str] = {}
        for seq, kind, trace_id, digest, payload, link, key_id in entries:
            seq = int(seq)
            if seq != expected_seq:
                broken += 1  # an entry was removed: the sequence has a gap
                expected_seq = seq
            expected_seq += 1
            if key_id is None:
                key: bytes | None = None
                usable = not self._mac_keys  # keyed stores never accept unkeyed links
            else:
                key = keys.get(str(key_id))
                usable = key is not None
            recomputed = (
                _chain_link(
                    key,
                    seq=seq,
                    kind=str(kind),
                    trace_id=trace_id,
                    replay_digest=digest,
                    payload=payload,
                    previous=previous,
                )
                if usable
                else None
            )
            if recomputed is None or not hmac.compare_digest(recomputed, str(link)):
                broken += 1
            previous = str(link)
            links[seq] = str(link)
            if kind == "trace" and trace_id is not None:
                chained_traces[seq] = (str(trace_id), str(digest))
            elif kind == "purge" and payload is not None:
                try:
                    ranges = json.loads(payload)["seqs"]
                    for first, last in ranges:
                        # A purge can only cover entries recorded before it.
                        purged.update(range(int(first), min(int(last), seq - 1) + 1))
                except (ValueError, KeyError, TypeError):
                    broken += 1
            else:
                broken += 1
        missing = 0
        mismatched = 0
        for seq, (trace_id, digest) in chained_traces.items():
            current = stored.get(trace_id)
            if current is None:
                if seq not in purged:
                    missing += 1
            elif current != digest:
                mismatched += 1
        chained_ids = {trace_id for trace_id, _ in chained_traces.values()}
        unsequenced = sum(1 for trace_id in stored if trace_id not in chained_ids)
        checkpoint_mismatch = False
        if checkpoint is not None:
            seq = int(checkpoint.get("seq", -1))
            link = str(checkpoint.get("link", ""))
            if seq == 0:
                checkpoint_mismatch = link != _CHAIN_GENESIS
            else:
                checkpoint_mismatch = links.get(seq) != link
        intact = not (broken or missing or mismatched or checkpoint_mismatch)
        head_seq = int(entries[-1][0]) if entries else 0
        return {
            "intact": intact,
            "complete": intact and unsequenced == 0,
            "entries": len(entries),
            "head": {"seq": head_seq, "link": previous},
            "broken_links": broken,
            "missing_traces": missing,
            "digest_mismatches": mismatched,
            "unsequenced_traces": unsequenced,
            "checkpoint_mismatch": checkpoint_mismatch,
        }

    def sequence_unsequenced(self) -> int:
        """Append valid traces that have no chain entry; return how many.

        For stores created before the chain existed. Traces are appended in
        trace_id order; this establishes a baseline for the current state and does
        not prove what happened before it. Invalid traces are left out.
        """
        with self._lock:
            try:
                rows = self._connection.execute(
                    "SELECT t.trace_id, t.replay_digest FROM audit_traces t "
                    "LEFT JOIN audit_chain c ON c.trace_id = t.trace_id "
                    "WHERE c.seq IS NULL ORDER BY t.trace_id"
                ).fetchall()
                appended = 0
                for trace_id, digest in rows:
                    if self._verify_locked(str(trace_id)) != "valid":
                        continue
                    self._append_chain_locked("trace", str(trace_id), str(digest), None)
                    appended += 1
                self._connection.commit()
            except BaseException:
                self._rollback_open_transaction()
                raise
        return appended

    def _relink_chain_locked(self) -> bool:
        """Recompute every link with the active key; only when the chain is intact."""
        if not self._mac_keys:
            return False
        key_id, key = self._mac_keys[0]
        entries = self._connection.execute(
            "SELECT seq, kind, trace_id, replay_digest, payload, key_id FROM audit_chain "
            "ORDER BY seq"
        ).fetchall()
        if all(row[5] == key_id for row in entries):
            return False
        previous = _CHAIN_GENESIS
        for seq, kind, trace_id, digest, payload, _ in entries:
            link = _chain_link(
                key,
                seq=int(seq),
                kind=str(kind),
                trace_id=trace_id,
                replay_digest=digest,
                payload=payload,
                previous=previous,
            )
            self._connection.execute(
                "UPDATE audit_chain SET link = ?, key_id = ? WHERE seq = ?",
                (link, key_id, seq),
            )
            previous = link
        return True

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
                   replay_digest, replay_version, replay_mac, mac_key_id,
                   check_trace_id, adjudication_sha256
            FROM audit_traces WHERE trace_id = ?
            """,
            (trace_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown audit trace: {trace_id}")
        fields = dict(zip(_R2_V3_FIELDS, row[:12], strict=True))
        stored_digest, version, stored_mac, mac_key_id = row[12], row[13], row[14], row[15]
        adjudication = dict(zip(_ADJUDICATION_FIELDS, row[16:18], strict=True))
        if version != _R2_V4 and any(value is not None for value in adjudication.values()):
            # Only r2-v4 binds an adjudication; one attached to an older trace is forged.
            return "invalid"
        if version == _R2_V4:
            events = _r2_v4_events({**fields, **adjudication})
        elif version == _R2_V3:
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
            expected_mac = _mac_for_trace(key, str(version), str(stored_digest), fields)
            if not hmac.compare_digest(expected_mac, str(stored_mac)):
                return "invalid"
        elif has_mac_metadata:
            # Never silently downgrade a previously keyed trace to digest-only
            # verification when the verification keys are missing.
            return "invalid"
        return "valid"

    def seal_unsealed(self) -> int:
        """MAC valid unsealed r2-v1, r2-v2, r2-v3 and r2-v4 traces; return how many.

        Only traces whose replay digest is still valid are sealed, with the active
        key. This establishes a keyed baseline for the current stored state; it
        cannot prove that a legacy trace was authentic before HMAC was enabled.
        Run once when enabling ATTRACTOR_AUDIT_HMAC_KEYS on an existing store.
        """
        if not self._mac_keys:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS is not configured")
        key_id, key = self._mac_keys[0]
        sealed = 0
        with self._lock:
            try:
                rows = self._connection.execute(
                    "SELECT trace_id, replay_digest, replay_version, "
                    "legacy_verification, verification, operation_status, evidence_count, "
                    "independent_evidence_count, verified_evidence_count, failure_count, "
                    "finding_count, schema_version, owner, recorded_at, software_version "
                    "FROM audit_traces "
                    "WHERE replay_version IN (?, ?, ?, ?) AND replay_mac IS NULL "
                    "AND mac_key_id IS NULL ORDER BY trace_id",
                    (_R2_V1, _R2_V2, _R2_V3, _R2_V4),
                ).fetchall()
                saved_keys, self._mac_keys = self._mac_keys, ()
                try:
                    valid = [row for row in rows if self._verify_locked(str(row[0])) == "valid"]
                finally:
                    self._mac_keys = saved_keys
                for row in valid:
                    trace_id, digest, version, *field_values = row
                    fields = dict(zip(_R2_V3_FIELDS, field_values, strict=True))
                    replay_mac = _mac_for_trace(key, str(version), str(digest), fields)
                    self._connection.execute(
                        "UPDATE audit_traces SET replay_mac = ?, mac_key_id = ? WHERE trace_id = ?",
                        (replay_mac, key_id, trace_id),
                    )
                    sealed += 1
                self._connection.commit()
            except BaseException:
                self._rollback_open_transaction()
                raise
        return sealed

    def reseal_with_active_key(self) -> dict[str, int]:
        """Re-MAC, with the active (first) key, every valid trace sealed by another key.

        Key rotation: put the new key first in ATTRACTOR_AUDIT_HMAC_KEYS and keep the
        old ones, run this, check ``verify_all()``, then the old keys can be retired.
        A trace is resealed only if it verifies under the configured keys, so an
        altered trace is never laundered into a valid one: it is counted in
        ``skipped_invalid`` and left as it is. Returns
        ``{"resealed": n, "skipped_invalid": m}``. The sequence chain is re-linked
        with the active key in the same call, only if ``verify_chain()`` reports it
        intact; check ``verify_chain()`` too before retiring the old keys.
        """
        if not self._mac_keys:
            raise ValueError("ATTRACTOR_AUDIT_HMAC_KEYS is not configured")
        key_id, key = self._mac_keys[0]
        counts = {"resealed": 0, "skipped_invalid": 0}
        # The sequence chain moves to the active key too, but only if it verifies
        # under the configured keys: a broken chain is never re-signed.
        with self._lock:
            try:
                # Checked under the same lock as the re-link, so no write can slip
                # in between the check and the re-signing.
                if self.verify_chain()["intact"]:
                    self._relink_chain_locked()
                rows = self._connection.execute(
                    "SELECT trace_id, replay_digest, replay_version, "
                    "legacy_verification, verification, operation_status, evidence_count, "
                    "independent_evidence_count, verified_evidence_count, failure_count, "
                    "finding_count, schema_version, owner, recorded_at, software_version "
                    "FROM audit_traces WHERE mac_key_id IS NOT NULL AND mac_key_id != ? "
                    "ORDER BY trace_id",
                    (key_id,),
                ).fetchall()
                for row in rows:
                    trace_id, digest, version, *field_values = row
                    if self._verify_locked(str(trace_id)) != "valid":
                        counts["skipped_invalid"] += 1
                        continue
                    fields = dict(zip(_R2_V3_FIELDS, field_values, strict=True))
                    replay_mac = _mac_for_trace(key, str(version), str(digest), fields)
                    self._connection.execute(
                        "UPDATE audit_traces SET replay_mac = ?, mac_key_id = ? WHERE trace_id = ?",
                        (replay_mac, key_id, trace_id),
                    )
                    counts["resealed"] += 1
                self._connection.commit()
            except BaseException:
                self._rollback_open_transaction()
                raise
        return counts

    def get(
        self,
        trace_id: str,
        requester: str | None = None,
        tenant_principals: Collection[str] | None = None,
    ) -> AuditTraceResponse | None:
        """Return the trace only to its owner or to a principal of the owner's tenant.

        ``tenant_principals`` (ADR-013) are the principals of the requester's tenant;
        a trace owned by any of them is readable. ``None`` means only the requester.

        ``requester`` is the authenticated principal, or None when authentication
        is off (single tenant: only traces without an owner exist to read). Traces
        without an owner are returned to authenticated principals only under the
        "shared" legacy policy. A trace the requester may not read is reported as
        missing (None), so the lookup does not reveal that it exists.
        """
        owners = sorted(
            {owner for owner in (requester, *(tenant_principals or ())) if owner is not None}
        )
        with self._lock:
            return self._get_locked(trace_id, requester, owners)

    def _get_locked(
        self, trace_id: str, requester: str | None, owners: Sequence[str]
    ) -> AuditTraceResponse | None:
        # One bound parameter per owner; owners come from the key registry, never
        # from the request, and the SQL text has no data in it.
        placeholders = ", ".join("?" for _ in owners) or "NULL"
        row = self._connection.execute(
            f"""
            SELECT trace_id, operation_status, evidence_count,
                   independent_evidence_count, verified_evidence_count,
                   failure_count, finding_count, replay_digest,
                   legacy_verification, replay_version, check_trace_id, adjudication_sha256
            FROM audit_traces WHERE trace_id = ? AND (
                (owner IS NULL AND (? IS NULL OR ? = 'shared')) OR owner IN ({placeholders})
            )
            """,  # nosec B608 - placeholders only
            (trace_id, requester, self._legacy_policy, *owners),
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
            check_trace_id=row[10],
            adjudication_sha256=row[11],
            replay_integrity=self.verify(trace_id),
        )
