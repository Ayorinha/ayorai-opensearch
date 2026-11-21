"""Durable idempotency outbox state machine for an ADR-010 Tessera adapter."""

from __future__ import annotations

import hmac
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ayorai_attractor.auditlog import HASH_SIZE

from .python_writer import CorruptStoreError, IdempotencyConflict, WriterError

MAX_IDEMPOTENCY_KEY_LENGTH = 256
MAX_CHECKPOINT_NOTE_BYTES = 64 * 1024


@dataclass(frozen=True)
class OutboxRecord:
    idempotency_key: str
    leaf_hash: bytes
    state: str
    tessera_index: int | None
    tree_size: int | None
    root_hash: bytes | None
    checkpoint_note: bytes | None
    replayed: bool = False


class SQLiteIdempotencyOutbox:
    """Durable reservation/assignment/recording state machine.

    PENDING means the key and salted leaf commitment are reserved locally.
    ASSIGNED means Tessera returned an index, which has been durably recorded.
    RECORDED means a signed checkpoint containing that index has been captured.
    A retry never re-appends a PENDING or ASSIGNED operation automatically:
    callers must reconcile it with Tessera or fail closed.
    """

    def __init__(self, database_path: str | Path, timeout: float = 10.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, int | float) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        if str(database_path) == ":memory:":
            raise ValueError("the outbox requires a file-backed SQLite database")
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = str(path)
        self._timeout = float(timeout)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout,
            isolation_level=None,
        )
        connection.execute(f"PRAGMA busy_timeout = {int(self._timeout * 1000)}")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            if mode is None or str(mode[0]).lower() != "wal":
                raise WriterError("SQLite WAL mode could not be enabled for the outbox")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS adr010_idempotency_outbox (
                    idempotency_key TEXT PRIMARY KEY
                        CHECK (length(idempotency_key) BETWEEN 1 AND 256),
                    leaf_hash BLOB NOT NULL CHECK (length(leaf_hash) = 32),
                    state TEXT NOT NULL
                        CHECK (state IN ('PENDING', 'ASSIGNED', 'RECORDED')),
                    tessera_index INTEGER,
                    tree_size INTEGER,
                    root_hash BLOB,
                    checkpoint_note BLOB,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CHECK (
                        (state = 'PENDING'
                            AND tessera_index IS NULL
                            AND tree_size IS NULL
                            AND root_hash IS NULL
                            AND checkpoint_note IS NULL)
                        OR
                        (state = 'ASSIGNED'
                            AND tessera_index IS NOT NULL
                            AND tessera_index >= 0
                            AND tree_size IS NULL
                            AND root_hash IS NULL
                            AND checkpoint_note IS NULL)
                        OR
                        (state = 'RECORDED'
                            AND tessera_index IS NOT NULL
                            AND tessera_index >= 0
                            AND tree_size IS NOT NULL
                            AND tree_size > tessera_index
                            AND root_hash IS NOT NULL
                            AND length(root_hash) = 32
                            AND checkpoint_note IS NOT NULL
                            AND length(checkpoint_note) > 0)
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_adr010_outbox_state_created
                ON adr010_idempotency_outbox (state, created_at);
                """
            )
            self._validate_rows(connection)
        finally:
            connection.close()

    @staticmethod
    def _validate_key_and_leaf(idempotency_key: str, leaf_hash: bytes) -> None:
        if (
            not isinstance(idempotency_key, str)
            or not idempotency_key.strip()
            or len(idempotency_key) > MAX_IDEMPOTENCY_KEY_LENGTH
        ):
            raise ValueError("idempotency_key must be 1–256 non-blank characters")
        if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
            raise ValueError("leaf_hash must be exactly 32 bytes")

    @staticmethod
    def _row_to_record(row: tuple[object, ...], replayed: bool = False) -> OutboxRecord:
        key, leaf, state, index, size, root, note = row
        if not isinstance(key, str) or not isinstance(leaf, bytes) or len(leaf) != HASH_SIZE:
            raise CorruptStoreError("outbox key or leaf hash is malformed")
        if state not in {"PENDING", "ASSIGNED", "RECORDED"}:
            raise CorruptStoreError("outbox state is unknown")
        if state == "PENDING" and any(value is not None for value in (index, size, root, note)):
            raise CorruptStoreError("PENDING outbox row contains remote receipt fields")
        if state == "ASSIGNED" and (
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            or any(value is not None for value in (size, root, note))
        ):
            raise CorruptStoreError("ASSIGNED outbox row is malformed")
        if state == "RECORDED" and (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= index
            or not isinstance(root, bytes)
            or len(root) != HASH_SIZE
            or not isinstance(note, bytes)
            or not note
            or len(note) > MAX_CHECKPOINT_NOTE_BYTES
        ):
            raise CorruptStoreError("RECORDED outbox row is malformed")
        return OutboxRecord(
            idempotency_key=key,
            leaf_hash=leaf,
            state=state,
            tessera_index=index,
            tree_size=size,
            root_hash=root,
            checkpoint_note=note,
            replayed=replayed,
        )

    @staticmethod
    def _validate_rows(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT idempotency_key, leaf_hash, state, tessera_index,
                   tree_size, root_hash, checkpoint_note
            FROM adr010_idempotency_outbox
            """
        ).fetchall()
        for row in rows:
            SQLiteIdempotencyOutbox._row_to_record(row)

    def reserve(self, idempotency_key: str, leaf_hash: bytes) -> OutboxRecord:
        """Reserve a key or return its existing state; never re-append on retry."""
        self._validate_key_and_leaf(idempotency_key, leaf_hash)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT idempotency_key, leaf_hash, state, tessera_index,
                       tree_size, root_hash, checkpoint_note
                FROM adr010_idempotency_outbox
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if row is not None:
                record = self._row_to_record(row, replayed=True)
                if not hmac.compare_digest(record.leaf_hash, leaf_hash):
                    raise IdempotencyConflict(
                        "the idempotency key already identifies a different leaf commitment"
                    )
                connection.commit()
                return record

            connection.execute(
                """
                INSERT INTO adr010_idempotency_outbox
                    (idempotency_key, leaf_hash, state)
                VALUES (?, ?, 'PENDING')
                """,
                (idempotency_key, leaf_hash),
            )
            connection.commit()
            return OutboxRecord(
                idempotency_key=idempotency_key,
                leaf_hash=leaf_hash,
                state="PENDING",
                tessera_index=None,
                tree_size=None,
                root_hash=None,
                checkpoint_note=None,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def assign(
        self,
        idempotency_key: str,
        leaf_hash: bytes,
        tessera_index: int,
    ) -> OutboxRecord:
        """Persist the index returned by Tessera before waiting for publication."""
        self._validate_key_and_leaf(idempotency_key, leaf_hash)
        if (
            isinstance(tessera_index, bool)
            or not isinstance(tessera_index, int)
            or tessera_index < 0
        ):
            raise ValueError("tessera_index must be a non-negative integer")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT idempotency_key, leaf_hash, state, tessera_index,
                       tree_size, root_hash, checkpoint_note
                FROM adr010_idempotency_outbox
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if row is None:
                raise CorruptStoreError("cannot assign an index to an unreserved key")
            record = self._row_to_record(row)
            if not hmac.compare_digest(record.leaf_hash, leaf_hash):
                raise IdempotencyConflict("reserved key has a different leaf commitment")
            if record.state == "PENDING":
                connection.execute(
                    """
                    UPDATE adr010_idempotency_outbox
                    SET state = 'ASSIGNED', tessera_index = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE idempotency_key = ?
                    """,
                    (tessera_index, idempotency_key),
                )
                connection.commit()
                return OutboxRecord(
                    idempotency_key=idempotency_key,
                    leaf_hash=leaf_hash,
                    state="ASSIGNED",
                    tessera_index=tessera_index,
                    tree_size=None,
                    root_hash=None,
                    checkpoint_note=None,
                )
            if record.tessera_index != tessera_index:
                raise CorruptStoreError("Tessera returned a different index for an existing key")
            connection.commit()
            return OutboxRecord(
                idempotency_key=record.idempotency_key,
                leaf_hash=record.leaf_hash,
                state=record.state,
                tessera_index=record.tessera_index,
                tree_size=record.tree_size,
                root_hash=record.root_hash,
                checkpoint_note=record.checkpoint_note,
                replayed=True,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_checkpoint(
        self,
        idempotency_key: str,
        leaf_hash: bytes,
        tessera_index: int,
        tree_size: int,
        root_hash: bytes,
        checkpoint_note: bytes,
    ) -> OutboxRecord:
        """Commit a verified checkpoint, or reconcile a PENDING row after restart."""
        self._validate_key_and_leaf(idempotency_key, leaf_hash)
        if isinstance(tessera_index, bool) or not isinstance(tessera_index, int) or tessera_index < 0:
            raise ValueError("tessera_index must be a non-negative integer")
        if (
            isinstance(tree_size, bool)
            or not isinstance(tree_size, int)
            or tree_size <= tessera_index
        ):
            raise ValueError("tree_size must be greater than tessera_index")
        if not isinstance(root_hash, bytes) or len(root_hash) != HASH_SIZE:
            raise ValueError("root_hash must be exactly 32 bytes")
        if (
            not isinstance(checkpoint_note, bytes)
            or not checkpoint_note
            or len(checkpoint_note) > MAX_CHECKPOINT_NOTE_BYTES
        ):
            raise ValueError("checkpoint_note must contain 1–65536 bytes")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT idempotency_key, leaf_hash, state, tessera_index,
                       tree_size, root_hash, checkpoint_note
                FROM adr010_idempotency_outbox
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if row is None:
                raise CorruptStoreError("cannot record a checkpoint for an unreserved key")
            record = self._row_to_record(row)
            if not hmac.compare_digest(record.leaf_hash, leaf_hash):
                raise IdempotencyConflict("reserved key has a different leaf commitment")
            if record.state == "ASSIGNED" and record.tessera_index != tessera_index:
                raise CorruptStoreError("reconciled index differs from the assigned Tessera index")
            if record.state == "RECORDED":
                if (
                    record.tessera_index != tessera_index
                    or record.tree_size != tree_size
                    or record.root_hash is None
                    or not hmac.compare_digest(record.root_hash, root_hash)
                    or record.checkpoint_note != checkpoint_note
                ):
                    raise CorruptStoreError("recorded checkpoint cannot be silently replaced")
                connection.commit()
                return OutboxRecord(
                    idempotency_key=record.idempotency_key,
                    leaf_hash=record.leaf_hash,
                    state=record.state,
                    tessera_index=record.tessera_index,
                    tree_size=record.tree_size,
                    root_hash=record.root_hash,
                    checkpoint_note=record.checkpoint_note,
                    replayed=True,
                )

            connection.execute(
                """
                UPDATE adr010_idempotency_outbox
                SET state = 'RECORDED',
                    tessera_index = ?,
                    tree_size = ?,
                    root_hash = ?,
                    checkpoint_note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE idempotency_key = ?
                """,
                (tessera_index, tree_size, root_hash, checkpoint_note, idempotency_key),
            )
            connection.commit()
            return OutboxRecord(
                idempotency_key=idempotency_key,
                leaf_hash=leaf_hash,
                state="RECORDED",
                tessera_index=tessera_index,
                tree_size=tree_size,
                root_hash=root_hash,
                checkpoint_note=checkpoint_note,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, idempotency_key: str) -> OutboxRecord | None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key must be non-blank")
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT idempotency_key, leaf_hash, state, tessera_index,
                       tree_size, root_hash, checkpoint_note
                FROM adr010_idempotency_outbox
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            return None if row is None else self._row_to_record(row)
        finally:
            connection.close()

    def list_unresolved(self) -> tuple[OutboxRecord, ...]:
        """Return PENDING and ASSIGNED rows for explicit recovery/reconciliation."""
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT idempotency_key, leaf_hash, state, tessera_index,
                       tree_size, root_hash, checkpoint_note
                FROM adr010_idempotency_outbox
                WHERE state IN ('PENDING', 'ASSIGNED')
                ORDER BY created_at, idempotency_key
                """
            ).fetchall()
            return tuple(self._row_to_record(row) for row in rows)
        finally:
            connection.close()
