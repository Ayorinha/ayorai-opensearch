"""Incremental SQLite Merkle-frontier prototype for ADR-010.

This is an isolated experiment, not production code. It stores the RFC 6962
frontier alongside leaf hashes so an append updates O(log n) nodes rather than
recomputing the entire tree. Full frontier/entry consistency is rebuilt and
checked on startup; inclusion proof generation still reads the selected prefix.
"""

from __future__ import annotations

import hmac
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ayorai_attractor.auditlog import (
    HASH_SIZE,
    empty_root,
    inclusion_proof,
    tree_root,
    verify_inclusion,
)
from ayorai_attractor.auditlog.merkle import node_hash

from .python_writer import (
    AppendReceipt,
    CorruptStoreError,
    IdempotencyConflict,
    TreeHead,
    WriterError,
)


@dataclass
class MerkleFrontier:
    """Compact range accumulator for RFC 6962 tree roots."""

    tree_size: int = 0
    nodes: dict[int, bytes] = field(default_factory=dict)

    def validate(self) -> None:
        if isinstance(self.tree_size, bool) or not isinstance(self.tree_size, int):
            raise CorruptStoreError("frontier tree size is not an integer")
        if self.tree_size < 0:
            raise CorruptStoreError("frontier tree size is negative")
        expected_levels = {
            level
            for level in range(self.tree_size.bit_length())
            if self.tree_size & (1 << level)
        }
        if set(self.nodes) != expected_levels:
            raise CorruptStoreError("frontier levels do not match the binary tree size")
        for level, digest in self.nodes.items():
            if (
                isinstance(level, bool)
                or not isinstance(level, int)
                or not isinstance(digest, bytes)
                or len(digest) != HASH_SIZE
            ):
                raise CorruptStoreError("frontier node is malformed")

    def append(self, leaf_hash: bytes) -> bytes:
        if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
            raise ValueError("leaf_hash must be exactly 32 bytes")
        self.validate()
        index = self.tree_size
        current = leaf_hash
        level = 0
        while index & (1 << level):
            left = self.nodes.pop(level, None)
            if left is None:
                raise CorruptStoreError("frontier is missing a required left subtree")
            current = node_hash(left, current)
            level += 1
        self.nodes[level] = current
        self.tree_size += 1
        self.validate()
        return self.root()

    def root(self) -> bytes:
        self.validate()
        if not self.nodes:
            return empty_root()
        levels = sorted(self.nodes)
        result = self.nodes[levels[0]]
        for level in levels[1:]:
            result = node_hash(self.nodes[level], result)
        return result

    @classmethod
    def from_leaves(cls, leaves: tuple[bytes, ...]) -> MerkleFrontier:
        frontier = cls()
        for leaf_hash in leaves:
            frontier.append(leaf_hash)
        return frontier


class SQLiteFrontierWriter:
    """Single-writer SQLite prototype with O(log n) frontier updates.

    The writer persists precomputed 32-byte leaf hashes only. Each append
    atomically updates the entry, tree size, and compact Merkle frontier.
    """

    def __init__(self, database_path: str | Path, timeout: float = 10.0) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, int | float) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        if str(database_path) == ":memory:":
            raise ValueError("the prototype requires a file-backed SQLite database")
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
                raise WriterError("SQLite WAL mode could not be enabled")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS adr010_frontier_metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    schema_version INTEGER NOT NULL,
                    tree_size INTEGER NOT NULL CHECK (tree_size >= 0)
                );

                CREATE TABLE IF NOT EXISTS adr010_frontier_entries (
                    leaf_index INTEGER PRIMARY KEY CHECK (leaf_index >= 0),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    leaf_hash BLOB NOT NULL CHECK (length(leaf_hash) = 32),
                    tree_size_at_append INTEGER NOT NULL CHECK (tree_size_at_append > 0),
                    root_hash_at_append BLOB NOT NULL CHECK (length(root_hash_at_append) = 32)
                );

                CREATE TABLE IF NOT EXISTS adr010_frontier_nodes (
                    level INTEGER PRIMARY KEY CHECK (level >= 0),
                    node_hash BLOB NOT NULL CHECK (length(node_hash) = 32)
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO adr010_frontier_metadata
                        (singleton, schema_version, tree_size)
                    VALUES (1, 1, 0)
                    """
                )
                self._load_snapshot(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        finally:
            connection.close()

    @staticmethod
    def _load_frontier(connection: sqlite3.Connection, tree_size: int) -> MerkleFrontier:
        rows = connection.execute(
            "SELECT level, node_hash FROM adr010_frontier_nodes ORDER BY level"
        ).fetchall()
        nodes: dict[int, bytes] = {}
        for level, digest in rows:
            if level in nodes:
                raise CorruptStoreError("frontier contains a duplicate level")
            if not isinstance(digest, bytes) or len(digest) != HASH_SIZE:
                raise CorruptStoreError("frontier node hash is malformed")
            nodes[level] = digest

        frontier = MerkleFrontier(tree_size=tree_size, nodes=nodes)
        frontier.validate()
        if tree_size == 0:
            latest = connection.execute(
                "SELECT COUNT(*) FROM adr010_frontier_entries"
            ).fetchone()
            if latest is None or latest[0] != 0:
                raise CorruptStoreError("empty frontier has persisted entries")
        else:
            latest = connection.execute(
                """
                SELECT leaf_index, tree_size_at_append, root_hash_at_append
                FROM adr010_frontier_entries
                ORDER BY leaf_index DESC
                LIMIT 1
                """
            ).fetchone()
            if latest is None:
                raise CorruptStoreError("frontier has no matching latest entry")
            leaf_index, size_at_append, root_at_append = latest
            if leaf_index != tree_size - 1 or size_at_append != tree_size:
                raise CorruptStoreError("latest entry does not match frontier tree size")
            if not isinstance(root_at_append, bytes) or not hmac.compare_digest(
                root_at_append, frontier.root()
            ):
                raise CorruptStoreError("frontier root differs from latest stored receipt")
        return frontier

    @staticmethod
    def _load_snapshot(
        connection: sqlite3.Connection,
    ) -> tuple[tuple[bytes, ...], MerkleFrontier]:
        metadata = connection.execute(
            """
            SELECT schema_version, tree_size
            FROM adr010_frontier_metadata
            WHERE singleton = 1
            """
        ).fetchone()
        if metadata is None:
            raise CorruptStoreError("frontier metadata row is missing")
        schema_version, tree_size = metadata
        if schema_version != 1:
            raise CorruptStoreError(f"unsupported frontier schema version: {schema_version}")

        rows = connection.execute(
            """
            SELECT leaf_index, leaf_hash, tree_size_at_append, root_hash_at_append
            FROM adr010_frontier_entries
            ORDER BY leaf_index
            """
        ).fetchall()
        if tree_size != len(rows):
            raise CorruptStoreError(
                f"frontier metadata tree_size={tree_size} but entry count={len(rows)}"
            )

        leaves: list[bytes] = []
        for expected_index, row in enumerate(rows):
            leaf_index, leaf_hash, size_at_append, root_at_append = row
            if leaf_index != expected_index:
                raise CorruptStoreError("frontier entry indices are not contiguous")
            if size_at_append != expected_index + 1:
                raise CorruptStoreError("frontier receipt tree size is inconsistent")
            if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
                raise CorruptStoreError("frontier entry leaf hash is malformed")
            if not isinstance(root_at_append, bytes) or len(root_at_append) != HASH_SIZE:
                raise CorruptStoreError("frontier entry root hash is malformed")
            leaves.append(leaf_hash)

        leaf_tuple = tuple(leaves)
        rebuilt = MerkleFrontier.from_leaves(leaf_tuple)
        persisted = SQLiteFrontierWriter._load_frontier(connection, tree_size)
        if rebuilt.nodes != persisted.nodes:
            raise CorruptStoreError("persisted frontier does not match the stored leaves")
        if not hmac.compare_digest(rebuilt.root(), tree_root(leaf_tuple)):
            raise CorruptStoreError("frontier root differs from the RFC 6962 tree root")
        if rows and not hmac.compare_digest(rows[-1][3], rebuilt.root()):
            raise CorruptStoreError("latest receipt root differs from rebuilt frontier")
        return leaf_tuple, rebuilt

    @staticmethod
    def _validate_append(idempotency_key: str, leaf_hash: bytes) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key must be a non-empty string")
        if len(idempotency_key) > 256:
            raise ValueError("idempotency_key must not exceed 256 characters")
        if not isinstance(leaf_hash, bytes) or len(leaf_hash) != HASH_SIZE:
            raise ValueError("leaf_hash must be exactly 32 bytes")

    def append(self, idempotency_key: str, leaf_hash: bytes) -> AppendReceipt:
        """Append one leaf using a compact frontier, or return its original receipt."""
        self._validate_append(idempotency_key, leaf_hash)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT leaf_index, leaf_hash, tree_size_at_append, root_hash_at_append
                FROM adr010_frontier_entries
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
                leaves, _ = self._load_snapshot(connection)
                if size_at_append > len(leaves):
                    raise CorruptStoreError("frontier receipt refers to a future tree size")
                proof = inclusion_proof(index, leaves[:size_at_append])
                if not verify_inclusion(index, size_at_append, leaf_hash, proof, stored_root):
                    raise CorruptStoreError("stored frontier receipt does not verify")
                connection.commit()
                return AppendReceipt(
                    index=index,
                    leaf_hash=bytes(stored_leaf),
                    tree_size=size_at_append,
                    root_hash=bytes(stored_root),
                    duplicate=True,
                )

            metadata = connection.execute(
                """
                SELECT schema_version, tree_size
                FROM adr010_frontier_metadata
                WHERE singleton = 1
                """
            ).fetchone()
            if metadata is None:
                raise CorruptStoreError("frontier metadata row is missing")
            schema_version, tree_size = metadata
            if schema_version != 1:
                raise CorruptStoreError(f"unsupported frontier schema version: {schema_version}")

            frontier = self._load_frontier(connection, tree_size)
            index = tree_size
            root_hash = frontier.append(leaf_hash)
            new_size = frontier.tree_size

            connection.execute("DELETE FROM adr010_frontier_nodes")
            connection.executemany(
                """
                INSERT INTO adr010_frontier_nodes (level, node_hash)
                VALUES (?, ?)
                """,
                sorted(frontier.nodes.items()),
            )
            connection.execute(
                """
                INSERT INTO adr010_frontier_entries
                    (leaf_index, idempotency_key, leaf_hash,
                     tree_size_at_append, root_hash_at_append)
                VALUES (?, ?, ?, ?, ?)
                """,
                (index, idempotency_key, leaf_hash, new_size, root_hash),
            )
            connection.execute(
                """
                UPDATE adr010_frontier_metadata
                SET tree_size = ?
                WHERE singleton = 1
                """,
                (new_size,),
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
        """Return the current tree head from the persisted frontier in O(log n)."""
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            metadata = connection.execute(
                """
                SELECT schema_version, tree_size
                FROM adr010_frontier_metadata
                WHERE singleton = 1
                """
            ).fetchone()
            if metadata is None or metadata[0] != 1:
                raise CorruptStoreError("frontier metadata is missing or unsupported")
            frontier = self._load_frontier(connection, metadata[1])
            connection.commit()
            return TreeHead(tree_size=frontier.tree_size, root_hash=frontier.root())
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def inclusion_proof(self, index: int, tree_size: int | None = None) -> tuple[bytes, ...]:
        """Return an inclusion proof from the persisted leaf prefix."""
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            leaves, _ = self._load_snapshot(connection)
            selected_size = len(leaves) if tree_size is None else tree_size
            if (
                isinstance(selected_size, bool)
                or not isinstance(selected_size, int)
                or not 0 < selected_size <= len(leaves)
            ):
                raise ValueError("tree_size must be between 1 and the current tree size")
            proof = inclusion_proof(index, leaves[:selected_size])
            connection.commit()
            return tuple(proof)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def verify_receipt(self, receipt: AppendReceipt) -> bool:
        """Verify persisted leaf contents and inclusion proof against a receipt."""
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
            leaves, _ = self._load_snapshot(connection)
            if (
                receipt.tree_size <= 0
                or receipt.tree_size > len(leaves)
                or not 0 <= receipt.index < receipt.tree_size
            ):
                connection.rollback()
                return False
            if not hmac.compare_digest(leaves[receipt.index], receipt.leaf_hash):
                connection.rollback()
                return False
            proof = inclusion_proof(receipt.index, leaves[: receipt.tree_size])
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
        """Compare a current or historical tree root with a caller-held checkpoint."""
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
            metadata = connection.execute(
                """
                SELECT schema_version, tree_size
                FROM adr010_frontier_metadata
                WHERE singleton = 1
                """
            ).fetchone()
            if metadata is None or metadata[0] != 1 or tree_size > metadata[1]:
                connection.rollback()
                return False
            if tree_size == 0:
                expected_root = empty_root()
            else:
                row = connection.execute(
                    """
                    SELECT root_hash_at_append
                    FROM adr010_frontier_entries
                    WHERE leaf_index = ?
                    """,
                    (tree_size - 1,),
                ).fetchone()
                if row is None or not isinstance(row[0], bytes):
                    connection.rollback()
                    return False
                expected_root = row[0]
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            return False
        finally:
            connection.close()
        return hmac.compare_digest(expected_root, root_hash)
