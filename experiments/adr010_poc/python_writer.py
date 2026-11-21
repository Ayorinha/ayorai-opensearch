"""Isolated ADR-010 persistence experiment; never imported by production code.

This prototype stores already-committed 32-byte Merkle leaves. It deliberately
does not create event records, salts, sign checkpoints, expose an API, or touch
the Judge. It exists only to test SQLite transaction and recovery mechanics.
"""

from __future__ import annotations

import hmac
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ayorai_attractor.auditlog import (
    HASH_SIZE,
    empty_root,
    inclusion_proof as merkle_inclusion_proof,
    tree_root,
    verify_inclusion,
)

_SCHEMA_VERSION = 1
_ZERO_HASH = bytes(HASH_SIZE)


class WriterError(RuntimeError):
    """Base exception for the isolated persistence prototype."""


class IdempotencyConflict(WriterError):
    """An idempotency key was reused with a different committed leaf."""


class CorruptStoreError(WriterError):
    """Persisted rows do not satisfy the prototype's structural invariants."""


@dataclass(frozen=True)
class AppendReceipt:
    """Local, unsigned receipt returned by the prototype."""

    index: int
    leaf_hash: bytes
    tree_size: int
    root_hash: bytes
    duplicate: bool = False


@dataclass(frozen=True)
class TreeHead:
    """Local, unsigned tree head; not an externally trusted checkpoint."""

    tree_size: int
    root_hash: bytes


class SQLiteMerkleWriter:
    """Single-writer SQLite prototype over precomputed RFC 6962 leaf hashes.

    Each append uses BEGIN IMMEDIATE and one SQLite transaction. The tree root
    is recomputed from all leaves before commit, making this intentionally
    simple and O(n) per append. This is a correctness prototype, not a scalable
    production writer or a signed transparency log.
    """

    def __init__(self, database_path: str | Path, timeout: float = 10.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, int | float) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        path = Path(database_path)
        if str(database_path) == ":memory:":
            raise ValueError("the prototype requires a file-backed SQLite database")
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
                raise WriterError("SQLite WAL mode could not be enabled")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS adr010_poc_metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    schema_version INTEGER NOT NULL,
                    tree_size INTEGER NOT NULL CHECK (tree_size >= 0)
                );

                CREATE TABLE IF NOT EXISTS adr010_poc_entries (
                    leaf_index INTEGER PRIMARY KEY CHECK (leaf_index >= 0),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    leaf_hash BLOB NOT NULL CHECK (length(leaf_hash) = 32),
                    tree_size_at_append INTEGER NOT NULL CHECK (tree_size_at_append > 0),
                    root_hash_at_append BLOB NOT NULL CHECK (length(root_hash_at_append) = 32)
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO adr010_poc_metadata
                        (singleton, schema_version, tree_size)
                    VALUES (1, ?, 0)
                    """,
                    (_SCHEMA_VERSION,),
                )
                self._load_snapshot(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        finally:
            connection.close()

    @staticmethod
    def _load_snapshot(connection: sqlite3.Connection) -> tuple[bytes, ...]:
        metadata = connection.execute(
            """
            SELECT schema_version, tree_size
            FROM adr010_poc_metadata
            WHERE singleton = 1
            """
        ).fetchone()
        if metadata is None:
            raise CorruptStoreError("metadata row is missing")
        schema_version, tree_size = metadata
        if schema_version != _SCHEMA_VERSION:
            raise CorruptStoreError(f"unsupported schema version: {schema_version}")

        rows = connection.execute(
            """
            SELECT leaf_index, leaf_hash, tree_size_at_append, root_hash_at_append
            FROM adr010_poc_entries
            ORDER BY leaf_index
            """
        ).fetchall()
        if tree_size != len(rows):
            raise CorruptStoreError(
                f"metadata tree_size={tree_size} but stored entry count={len(rows)}"
            )

        hashes: list[bytes] = []
        for expected_index, row in enumerate(rows):
            leaf_index, leaf_hash, size_at_append, root_at_append = row
            if leaf_index != expected_index:
                raise CorruptStoreError("entry indices are not contiguous")
            if size_at_append != expected_index + 1:
                raise CorruptStoreError("stored receipt tree size is inconsistent")
            if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
                raise CorruptStoreError("stored leaf hash is malformed")
            if not isinstance(root_at_append, bytes) or len(root_at_append) != HASH_SIZE:
                raise CorruptStoreError("stored receipt root is malformed")
            hashes.append(leaf_hash)
        return tuple(hashes)

    @staticmethod
    def _validate_append(idempotency_key: str, leaf_hash: bytes) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key must be a non-empty string")
        if len(idempotency_key) > 256:
            raise ValueError("idempotency_key must not exceed 256 characters")
        if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
            raise ValueError("leaf_hash must be exactly 32 bytes")

    def append(self, idempotency_key: str, leaf_hash: bytes) -> AppendReceipt:
        """Append one precomputed leaf atomically or return its original receipt."""
        self._validate_append(idempotency_key, leaf_hash)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT leaf_index, leaf_hash, tree_size_at_append, root_hash_at_append
                FROM adr010_poc_entries
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

            if existing is not None:
                index, stored_leaf, size_at_append, stored_root = existing
                if not hmac.compare_digest(bytes(stored_leaf), leaf_hash):
                    raise IdempotencyConflict(
                        "the idempotency key already identifies a different leaf"
                    )
                hashes = self._load_snapshot(connection)
                if size_at_append > len(hashes):
                    raise CorruptStoreError("receipt refers to a future tree size")
                expected_root = tree_root(hashes[:size_at_append])
                if not hmac.compare_digest(expected_root, bytes(stored_root)):
                    raise CorruptStoreError("stored receipt does not match its tree prefix")
                connection.commit()
                return AppendReceipt(
                    index=index,
                    leaf_hash=bytes(stored_leaf),
                    tree_size=size_at_append,
                    root_hash=bytes(stored_root),
                    duplicate=True,
                )

            metadata = connection.execute(
                "SELECT tree_size FROM adr010_poc_metadata WHERE singleton = 1"
            ).fetchone()
            if metadata is None:
                raise CorruptStoreError("metadata row is missing")
            index = metadata[0]
            new_size = index + 1
            connection.execute(
                """
                INSERT INTO adr010_poc_entries
                    (leaf_index, idempotency_key, leaf_hash,
                     tree_size_at_append, root_hash_at_append)
                VALUES (?, ?, ?, ?, ?)
                """,
                (index, idempotency_key, leaf_hash, new_size, _ZERO_HASH),
            )
            connection.execute(
                "UPDATE adr010_poc_metadata SET tree_size = ? WHERE singleton = 1",
                (new_size,),
            )
            hashes = self._load_snapshot(connection)
            root_hash = tree_root(hashes)
            connection.execute(
                """
                UPDATE adr010_poc_entries
                SET root_hash_at_append = ?
                WHERE leaf_index = ?
                """,
                (root_hash, index),
            )
            connection.commit()
            return AppendReceipt(
                index=index,
                leaf_hash=leaf_hash,
                tree_size=new_size,
                root_hash=root_hash,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def tree_head(self) -> TreeHead:
        """Return a consistent local tree head from one SQLite read transaction."""
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            hashes = self._load_snapshot(connection)
            connection.commit()
            root_hash = tree_root(hashes) if hashes else empty_root()
            return TreeHead(tree_size=len(hashes), root_hash=root_hash)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def inclusion_proof(self, index: int, tree_size: int | None = None) -> tuple[bytes, ...]:
        """Return a proof for an entry at the selected persisted tree size."""
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            hashes = self._load_snapshot(connection)
            selected_size = len(hashes) if tree_size is None else tree_size
            if (
                isinstance(selected_size, bool)
                or not isinstance(selected_size, int)
                or not 0 < selected_size <= len(hashes)
            ):
                raise ValueError("tree_size must be between 1 and the current tree size")
            proof = merkle_inclusion_proof(index, hashes[:selected_size])
            connection.commit()
            return tuple(proof)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def verify_receipt(self, receipt: AppendReceipt) -> bool:
        """Verify the persisted leaf and proof against the receipt's tree prefix."""
        if not isinstance(receipt, AppendReceipt):
            return False
        if (
            isinstance(receipt.index, bool)
            or not isinstance(receipt.index, int)
            or isinstance(receipt.tree_size, bool)
            or not isinstance(receipt.tree_size, int)
            or not isinstance(receipt.leaf_hash, bytes | bytearray)
            or len(receipt.leaf_hash) != HASH_SIZE
            or not isinstance(receipt.root_hash, bytes | bytearray)
            or len(receipt.root_hash) != HASH_SIZE
        ):
            return False

        connection = self._connect()
        try:
            connection.execute("BEGIN")
            hashes = self._load_snapshot(connection)
            if (
                receipt.tree_size <= 0
                or receipt.tree_size > len(hashes)
                or not 0 <= receipt.index < receipt.tree_size
            ):
                connection.rollback()
                return False
            stored_leaf = hashes[receipt.index]
            if not hmac.compare_digest(stored_leaf, receipt.leaf_hash):
                connection.rollback()
                return False
            proof = merkle_inclusion_proof(receipt.index, hashes[: receipt.tree_size])
            connection.commit()
        except (ValueError, CorruptStoreError, sqlite3.Error, TypeError):
            connection.rollback()
            return False
        finally:
            connection.close()

        return verify_inclusion(
            receipt.index,
            receipt.tree_size,
            receipt.leaf_hash,
            proof,
            receipt.root_hash,
        )

    def matches_checkpoint(self, tree_size: int, root_hash: bytes) -> bool:
        """Compare local history with a caller-held checkpoint (not stored here)."""
        if (
            isinstance(tree_size, bool)
            or not isinstance(tree_size, int)
            or tree_size < 0
            or not isinstance(root_hash, bytes)
            or len(root_hash) != HASH_SIZE
        ):
            return False
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            hashes = self._load_snapshot(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        if tree_size > len(hashes):
            return False
        prefix = hashes[:tree_size]
        computed = tree_root(prefix) if prefix else empty_root()
        return hmac.compare_digest(computed, root_hash)
