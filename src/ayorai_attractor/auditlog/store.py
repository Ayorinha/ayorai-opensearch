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
    consistency_proof,
    inclusion_proof,
    leaf_hash,
    tree_root,
    verify_inclusion,
)
from ayorai_attractor.auditlog.note import NoteSigner, parse_checkpoint, verify_note

LEAF_SCHEMA = "ayorai.verify-leaf.v1"
RECORD_SCHEMA = "ayorai.verify-record.v1"
RECEIPT_VERSION = "ayorai.verify-receipt.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_IDEMPOTENCY_KEY = re.compile(r"[\x21-\x7e]{1,128}")


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

    def __post_init__(self) -> None:
        for name in ("input_sha256", "output_sha256", "rules_sha256"):
            if _SHA256.fullmatch(getattr(self, name)) is None:
                raise ValueError(f"{name} must be 64 lowercase hex characters")
        if not self.decision_state or not self.client or not self.software_id:
            raise ValueError("decision_state, client and software_id are required")


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
                self._hashes: list[bytes] = []
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
        self._hashes = []
        for idx, leaf, stored in self._connection.execute(
            "SELECT idx, leaf, leaf_hash FROM vlog_leaves ORDER BY idx"
        ):
            if idx != len(self._hashes) or leaf_hash(bytes(leaf)) != bytes(stored):
                raise LogCorruption(f"leaf {idx} does not match its stored hash or position")
            self._hashes.append(bytes(stored))

    def _checkpoint_note(self, size: int, root: bytes) -> str:
        body = f"{self.origin}\n{size}\n{_b64(root)}\n"
        return self.signer.sign(body)

    # -- public API --------------------------------------------------------------

    @property
    def verifier_key(self) -> str:
        return self.signer.verifier_key

    def size(self) -> int:
        with self._lock:
            return len(self._hashes)

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
                count = int(
                    self._connection.execute("SELECT COUNT(*) FROM vlog_leaves").fetchone()[0]
                )
                if count != len(self._hashes):
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
        index = len(self._hashes)
        hashed = leaf_hash(leaf)
        self._connection.execute(
            "INSERT INTO vlog_leaves (idx, leaf, leaf_hash) VALUES (?, ?, ?)", (index, leaf, hashed)
        )
        self._connection.execute(
            "INSERT INTO vlog_records (idx, salt, record) VALUES (?, ?, ?)",
            (index, salt, json.dumps(record, sort_keys=True, ensure_ascii=False)),
        )
        self._hashes.append(hashed)
        size = len(self._hashes)
        note = self._checkpoint_note(size, tree_root(self._hashes))
        self._connection.execute(
            "INSERT INTO vlog_checkpoints (size, note) VALUES (?, ?)", (size, note)
        )
        receipt = {
            "receipt_version": RECEIPT_VERSION,
            "index": index,
            "leaf": _b64(leaf),
            "inclusion_proof": [_b64(node) for node in inclusion_proof(index, self._hashes)],
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
            if not 0 < old_size <= len(self._hashes):
                raise ValueError("old_size must be between 1 and the current size")
            return [_b64(node) for node in consistency_proof(old_size, self._hashes)]

    def erase(self, index: int, erased_at: str) -> bool:
        """Delete salt and record of one event (LGPD); the public tree is unchanged."""
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE vlog_records SET salt = NULL, record = NULL, erased_at = ? "
                "WHERE idx = ? AND erased_at IS NULL",
                (erased_at, index),
            )
            return cursor.rowcount == 1

    def verify_log(self) -> dict[str, Any]:
        """Re-derive the tree and check every stored checkpoint (signature, size and root)."""
        with self._lock:
            hashes: list[bytes] = []
            problems: list[str] = []
            for idx, leaf, stored in self._connection.execute(
                "SELECT idx, leaf, leaf_hash FROM vlog_leaves ORDER BY idx"
            ):
                if idx != len(hashes):
                    problems.append(f"gap before leaf {idx}")
                if leaf_hash(bytes(leaf)) != bytes(stored):
                    problems.append(f"leaf {idx} hash mismatch")
                hashes.append(leaf_hash(bytes(leaf)))
            checkpoints = self._connection.execute(
                "SELECT size, note FROM vlog_checkpoints ORDER BY size"
            ).fetchall()
            for size, note in checkpoints:
                body = verify_note(str(note), self.verifier_key)
                parsed = parse_checkpoint(body) if body is not None else None
                if parsed is None or parsed.origin != self.origin or parsed.size != size:
                    problems.append(f"checkpoint {size}: bad signature or body")
                elif size > len(hashes) or tree_root(hashes[:size]) != parsed.root:
                    problems.append(f"checkpoint {size}: root does not match the tree")
            latest = int(checkpoints[-1][0]) if checkpoints else 0
            if latest != len(hashes):
                problems.append(f"latest checkpoint covers {latest} of {len(hashes)} leaves")
            erased = int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM vlog_records WHERE erased_at IS NOT NULL"
                ).fetchone()[0]
            )
            return {
                "valid": not problems,
                "size": len(hashes),
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
