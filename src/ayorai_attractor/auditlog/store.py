"""Verification-event log: Merkle tree, signed checkpoints and receipts (ADR-010, phases 2–3).

One SQLite database, one writer at a time (``BEGIN IMMEDIATE``), so several
processes on one host may share it. Every appended event:

1. builds the salted ``record`` (decision 1) — input and output digests, decision
   state, **verdict** (decision 2: only inside the commitment), a pseudonymous
   client identifier and the untrusted server time;
2. stores ``salt`` and ``record`` in the erasable table;
3. appends the public **leaf** — schema, ``rules_sha256``, ``software_id`` and the
   commitment, never the verdict — to the RFC 6962 tree;
4. signs a C2SP checkpoint of the new tree and returns a **receipt** with the
   leaf, the inclusion proof, the signed checkpoint, the salt and the record.

The client can verify the receipt offline with ``verify_receipt`` and the log's
verifier key. ``erase`` removes salt and record (LGPD) while the tree stays
valid. ``verify_log`` re-derives every leaf hash and checks the latest and every
stored checkpoint against the tree.

What this does not provide (ADR-010, "Guarantees and limits"): protection against
an operator who controls the database and the signing key. That needs external
state — witnesses, timestamps or client-held receipts and checkpoints.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rfc8785

from ayorai_attractor.auditlog.commitment import commit, new_salt, verify_commitment
from ayorai_attractor.auditlog.merkle import (
    IncrementalTree,
    leaf_hash,
    tree_root,
    verify_inclusion,
)
from ayorai_attractor.auditlog.note import NoteSigner, parse_checkpoint, verify_note

LEAF_SCHEMA = "ayorai.verify-leaf.v1"
RECORD_SCHEMA = "ayorai.verify-record.v2"  # v1 plus tenant (ADR-013)
ERASURE_SCHEMA = "ayorai.verify-erasure.v1"
RECEIPT_VERSION = "ayorai.verify-receipt.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_IDEMPOTENCY_KEY = re.compile(r"[\x21-\x7e]{1,128}")
_TENANT = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


class IdempotencyConflict(ValueError):
    """The idempotency key was already used for a different input."""


class LogCorruption(RuntimeError):
    """The stored log does not match its own signed checkpoints."""


@dataclass(frozen=True)
class VerificationEvent:
    input_sha256: str
    output_sha256: str
    rules_sha256: str
    decision_state: str
    verdict: str | None
    client: str
    received_at: str
    software_id: str
    tenant: str = "default"

    def __post_init__(self) -> None:
        for name in ("input_sha256", "output_sha256", "rules_sha256"):
            if _SHA256.fullmatch(getattr(self, name)) is None:
                raise ValueError(f"{name} must be 64 lowercase hex characters")
        if not self.decision_state or not self.client or not self.software_id:
            raise ValueError("decision_state, client and software_id are required")
        if _TENANT.fullmatch(self.tenant) is None:
            raise ValueError("tenant must match [a-z0-9][a-z0-9._-]{0,63}")


def valid_idempotency_key(value: str) -> bool:
    return _IDEMPOTENCY_KEY.fullmatch(value) is not None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class VerificationLog:
    def __init__(self, path: str, signer: NoteSigner) -> None:
        self.path = path
        self.signer = signer
        self.origin = signer.name
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._connection.execute("PRAGMA busy_timeout = 5000")
        try:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS vlog_leaves (
                    idx INTEGER PRIMARY KEY, leaf BLOB NOT NULL, leaf_hash BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS vlog_records (
                    idx INTEGER PRIMARY KEY, salt BLOB, record TEXT, erased_at TEXT);
                CREATE TABLE IF NOT EXISTS vlog_idempotency (
                    key_digest TEXT PRIMARY KEY, input_sha256 TEXT NOT NULL,
                    idx INTEGER NOT NULL, receipt TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS vlog_checkpoints (
                    size INTEGER PRIMARY KEY, note TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS vlog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """
            )
            with self._lock:
                self._bind_origin()
                self._tree = IncrementalTree()
                self._reload_hashes()
        except BaseException:
            # Refusing a database (other origin, corruption) must not leak the connection.
            self._connection.close()
            raise

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> VerificationLog:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- internals ---------------------------------------------------------------

    def _bind_origin(self) -> None:
        """A database belongs to one origin and one verifier key; refuse to mix them."""
        rows = dict(self._connection.execute("SELECT key, value FROM vlog_meta").fetchall())
        if not rows:
            self._connection.execute(
                "INSERT INTO vlog_meta (key, value) VALUES ('origin', ?), ('verifier_key', ?)",
                (self.origin, self.signer.verifier_key),
            )
            return
        if (
            rows.get("origin") != self.origin
            or rows.get("verifier_key") != self.signer.verifier_key
        ):
            raise LogCorruption("the database belongs to another log origin or signing key")

    def _reload_hashes(self) -> None:
        tree = IncrementalTree()
        for idx, leaf, stored in self._connection.execute(
            "SELECT idx, leaf, leaf_hash FROM vlog_leaves ORDER BY idx"
        ):
            if idx != len(tree) or leaf_hash(bytes(leaf)) != bytes(stored):
                raise LogCorruption(f"leaf {idx} does not match its stored hash or position")
            tree.append(bytes(stored))
        self._tree = tree

    def _stored_size(self) -> int:
        """Leaves in the database; O(log n) through the primary key (COUNT(*) is O(n))."""
        row = self._connection.execute("SELECT MAX(idx) FROM vlog_leaves").fetchone()
        return 0 if row[0] is None else int(row[0]) + 1

    def _checkpoint_note(self, size: int, root: bytes) -> str:
        body = f"{self.origin}\n{size}\n{_b64(root)}\n"
        return self.signer.sign(body)

    # -- public API --------------------------------------------------------------

    @property
    def verifier_key(self) -> str:
        return self.signer.verifier_key

    def size(self) -> int:
        with self._lock:
            return len(self._tree)

    def latest_checkpoint(self) -> str:
        with self._lock:
            row = self._connection.execute(
                "SELECT note FROM vlog_checkpoints ORDER BY size DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return self._checkpoint_note(0, tree_root([]))
            return str(row[0])

    def append(
        self, event: VerificationEvent, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """Record one event and return its receipt (same key and input → same receipt)."""
        if idempotency_key is not None and not valid_idempotency_key(idempotency_key):
            raise ValueError("Idempotency-Key must be 1-128 visible ASCII characters")
        key_digest = (
            hashlib.sha256(f"{event.client}\x00{idempotency_key}".encode()).hexdigest()
            if idempotency_key is not None
            else None
        )
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                if key_digest is not None:
                    row = self._connection.execute(
                        "SELECT input_sha256, receipt FROM vlog_idempotency WHERE key_digest = ?",
                        (key_digest,),
                    ).fetchone()
                    if row is not None:
                        self._connection.execute("COMMIT")
                        if row[0] != event.input_sha256:
                            raise IdempotencyConflict(
                                "Idempotency-Key was already used for a different input"
                            )
                        stored: dict[str, Any] = json.loads(row[1])
                        return stored
                # Another process may have appended since this one last read the tree.
                count = self._stored_size()
                if count != len(self._tree):
                    self._reload_hashes()
                receipt = self._append_locked(event, key_digest)
                self._connection.execute("COMMIT")
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                self._reload_hashes()
                raise
            return receipt

    def _append_locked(self, event: VerificationEvent, key_digest: str | None) -> dict[str, Any]:
        record = {
            "schema": RECORD_SCHEMA,
            "input_sha256": event.input_sha256,
            "output_sha256": event.output_sha256,
            "decision_state": event.decision_state,
            "verdict": event.verdict,
            "client": event.client,
            "tenant": event.tenant,
            "received_at": event.received_at,
            "time_source": "server_clock",
        }
        salt = new_salt()
        leaf = rfc8785.dumps(
            {
                "schema": LEAF_SCHEMA,
                "rules_sha256": event.rules_sha256,
                "software_id": event.software_id,
                "commitment": commit(record, salt).hex(),
            }
        )
        index = self._append_leaf_locked(leaf)
        self._connection.execute(
            "INSERT INTO vlog_records (idx, salt, record) VALUES (?, ?, ?)",
            (index, salt, json.dumps(record, sort_keys=True, ensure_ascii=False)),
        )
        note = str(
            self._connection.execute(
                "SELECT note FROM vlog_checkpoints WHERE size = ?", (index + 1,)
            ).fetchone()[0]
        )
        receipt = {
            "receipt_version": RECEIPT_VERSION,
            "index": index,
            "leaf": _b64(leaf),
            "inclusion_proof": [_b64(node) for node in self._tree.inclusion_proof(index)],
            "checkpoint": note,
            "salt": _b64(salt),
            "record": record,
        }
        if key_digest is not None:
            self._connection.execute(
                "INSERT INTO vlog_idempotency (key_digest, input_sha256, idx, receipt) "
                "VALUES (?, ?, ?, ?)",
                (key_digest, event.input_sha256, index, json.dumps(receipt, sort_keys=True)),
            )
        return receipt

    def consistency(self, old_size: int) -> list[str]:
        """RFC 6962 consistency proof from ``old_size`` to the current tree (for witnesses)."""
        with self._lock:
            if not 0 < old_size <= len(self._tree):
                raise ValueError("old_size must be between 1 and the current size")
            return [_b64(node) for node in self._tree.consistency_proof(old_size)]

    def erase(self, index: int, erased_at: str, reason: str = "data_subject_request") -> int | None:
        """Delete salt and record of one event (LGPD) and log the erasure itself.

        The erasure is a new public leaf ``{schema, erased_index, erased_at, reason}``
        with no personal data, under a new signed checkpoint. The erased event's leaf
        stays in the tree, so the tree and every client-held receipt remain valid.
        Returns the index of the erasure leaf, or ``None`` if there was nothing to
        erase (unknown index, an erasure leaf, or already erased).
        """
        if re.fullmatch(r"[a-z_]{1,64}", reason) is None:
            raise ValueError("reason must be a short lowercase code")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                count = self._stored_size()
                if count != len(self._tree):
                    self._reload_hashes()
                cursor = self._connection.execute(
                    "UPDATE vlog_records SET salt = NULL, record = NULL, erased_at = ? "
                    "WHERE idx = ? AND erased_at IS NULL AND record IS NOT NULL",
                    (erased_at, index),
                )
                if cursor.rowcount != 1:
                    self._connection.execute("ROLLBACK")
                    return None
                leaf = rfc8785.dumps(
                    {
                        "schema": ERASURE_SCHEMA,
                        "erased_index": index,
                        "erased_at": erased_at,
                        "reason": reason,
                    }
                )
                erasure_index = self._append_leaf_locked(leaf)
                self._connection.execute("COMMIT")
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                self._reload_hashes()
                raise
            return erasure_index

    def _append_leaf_locked(self, leaf: bytes) -> int:
        """Append a public leaf and sign the new checkpoint (inside the caller's transaction)."""
        index = len(self._tree)
        hashed = leaf_hash(leaf)
        self._connection.execute(
            "INSERT INTO vlog_leaves (idx, leaf, leaf_hash) VALUES (?, ?, ?)", (index, leaf, hashed)
        )
        self._tree.append(hashed)
        size = len(self._tree)
        note = self._checkpoint_note(size, self._tree.root())
        self._connection.execute(
            "INSERT INTO vlog_checkpoints (size, note) VALUES (?, ?)", (size, note)
        )
        return index

    def matches_checkpoint(self, note: str) -> bool:
        """Is a checkpoint held outside the host (client, witness) part of this log?

        False when the note is not signed by this log, when it covers more leaves
        than the log now has (truncation or restore of an older copy) or when its
        root differs from the root of the same prefix here (rewritten history).
        """
        body = verify_note(note, self.verifier_key)
        parsed = parse_checkpoint(body) if body is not None else None
        if parsed is None or parsed.origin != self.origin:
            return False
        with self._lock:
            if parsed.size > len(self._tree):
                return False
            return self._tree.root(parsed.size) == parsed.root

    def backup(self, destination: str) -> int:
        """Consistent online copy to a new file (SQLite backup API); returns the tree size."""
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
            return int(copy.execute("SELECT COUNT(*) FROM vlog_leaves").fetchone()[0])
        finally:
            copy.close()

    def verify_log(self) -> dict[str, Any]:
        """Re-derive the tree and check every stored checkpoint (signature, size and root)."""
        with self._lock:
            tree = IncrementalTree()
            problems: list[str] = []
            for idx, leaf, stored in self._connection.execute(
                "SELECT idx, leaf, leaf_hash FROM vlog_leaves ORDER BY idx"
            ):
                if idx != len(tree):
                    problems.append(f"gap before leaf {idx}")
                if leaf_hash(bytes(leaf)) != bytes(stored):
                    problems.append(f"leaf {idx} hash mismatch")
                tree.append(leaf_hash(bytes(leaf)))
            checkpoints = self._connection.execute(
                "SELECT size, note FROM vlog_checkpoints ORDER BY size"
            ).fetchall()
            for size, note in checkpoints:
                body = verify_note(str(note), self.verifier_key)
                parsed = parse_checkpoint(body) if body is not None else None
                if parsed is None or parsed.origin != self.origin or parsed.size != size:
                    problems.append(f"checkpoint {size}: bad signature or body")
                elif size > len(tree) or tree.root(size) != parsed.root:
                    problems.append(f"checkpoint {size}: root does not match the tree")
            latest = int(checkpoints[-1][0]) if checkpoints else 0
            if latest != len(tree):
                problems.append(f"latest checkpoint covers {latest} of {len(tree)} leaves")
            # Bind every restricted record to its public event commitment. The
            # Merkle tree authenticates the leaf, not the mutable record table.
            erasure_leaves: dict[int, int] = {}
            event_leaves: set[int] = set()
            event_fields: dict[int, dict[str, Any]] = {}
            for idx, leaf in self._connection.execute(
                "SELECT idx, leaf FROM vlog_leaves ORDER BY idx"
            ):
                try:
                    fields = json.loads(bytes(leaf))
                except (TypeError, ValueError):
                    problems.append(f"leaf {idx} is not JSON")
                    continue
                if isinstance(fields, dict) and fields.get("schema") == LEAF_SCHEMA:
                    event_index = int(idx)
                    event_leaves.add(event_index)
                    event_fields[event_index] = fields
                elif isinstance(fields, dict) and fields.get("schema") == ERASURE_SCHEMA:
                    target = fields.get("erased_index")
                    if type(target) is not int or not 0 <= target < idx or target not in event_leaves:
                        problems.append(f"erasure leaf {idx} names an invalid event")
                    elif target in erasure_leaves:
                        problems.append(f"event {target} has multiple erasure leaves")
                    else:
                        erasure_leaves[target] = int(idx)

            record_rows = self._connection.execute(
                "SELECT idx, salt, record, erased_at FROM vlog_records ORDER BY idx"
            ).fetchall()
            record_indices: set[int] = set()
            erased = 0
            for idx, salt, record_text, erased_at in record_rows:
                record_index = int(idx)
                record_indices.add(record_index)
                if record_index not in event_leaves:
                    problems.append(f"record {record_index} has no event leaf")
                    continue
                if erased_at is not None:
                    erased += 1
                    if salt is not None or record_text is not None:
                        problems.append(f"record {record_index} has residual data after erasure")
                    if record_index not in erasure_leaves:
                        problems.append(f"record {record_index} erased without an erasure event")
                    continue
                if salt is None or record_text is None:
                    problems.append(f"record {record_index} is incomplete or partially erased")
                    continue
                try:
                    record_value = json.loads(str(record_text))
                    commitment = bytes.fromhex(str(event_fields[record_index].get("commitment", "")))
                    valid_commitment = verify_commitment(commitment, record_value, salt)
                except (KeyError, TypeError, ValueError):
                    valid_commitment = False
                if not valid_commitment:
                    problems.append(f"record {record_index} commitment mismatch")

            for event_index in event_leaves:
                if event_index not in record_indices and event_index not in erasure_leaves:
                    problems.append(f"record {event_index} is missing")
            return {
                "valid": not problems,
                "size": len(tree),
                "checkpoints": len(checkpoints),
                "erased_records": erased,
                "problems": problems,
            }


def verify_receipt(receipt: Mapping[str, Any], vkey: str) -> bool:
    """Offline verification of a receipt against the log's verifier key.

    Checks the checkpoint signature, the inclusion of the leaf in that checkpoint
    and that the leaf's commitment opens to the given record and salt.
    """
    try:
        if receipt.get("receipt_version") != RECEIPT_VERSION:
            return False
        body = verify_note(str(receipt["checkpoint"]), vkey)
        checkpoint = parse_checkpoint(body) if body is not None else None
        if checkpoint is None:
            return False
        leaf = base64.b64decode(str(receipt["leaf"]), validate=True)
        proof = [base64.b64decode(str(node), validate=True) for node in receipt["inclusion_proof"]]
        index = receipt["index"]
        if not isinstance(index, int) or isinstance(index, bool):
            return False
        if not verify_inclusion(index, checkpoint.size, leaf_hash(leaf), proof, checkpoint.root):
            return False
        leaf_fields = json.loads(leaf)
        if leaf_fields.get("schema") != LEAF_SCHEMA:
            return False
        commitment = bytes.fromhex(str(leaf_fields["commitment"]))
        salt = base64.b64decode(str(receipt["salt"]), validate=True)
        record = receipt["record"]
        return isinstance(record, Mapping) and verify_commitment(commitment, record, salt)
    except (KeyError, TypeError, ValueError):
        return False
