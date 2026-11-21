"""Fail-closed orchestration contract for an AYORAI-to-Tessera adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ayorai_attractor.auditlog import HASH_SIZE

from .idempotency_outbox import OutboxRecord, SQLiteIdempotencyOutbox
from .python_writer import CorruptStoreError, WriterError


class ReconciliationRequired(WriterError):
    """The outbox is unresolved and must not trigger another Tessera append."""


@dataclass(frozen=True)
class VerifiedCheckpoint:
    """Checkpoint bytes already signature- and origin-verified by the client."""

    tree_size: int
    root_hash: bytes
    checkpoint_note: bytes


class TesseraClient(Protocol):
    """Narrow boundary required from a real Tessera client/scanner."""

    def append(self, leaf_hash: bytes) -> int:
        """Append a leaf and return its durable Tessera index."""

    def find_entries(self, leaf_hash: bytes) -> list[int]:
        """Find every durable index containing this exact leaf hash."""

    def wait_for_checkpoint(self, tessera_index: int) -> VerifiedCheckpoint:
        """Wait until a verified signed checkpoint includes the supplied index."""


class TesseraOutboxAdapter:
    """Coordinate a durable outbox with a separate Tessera process.

    A new reservation may append once. A replayed PENDING row is never appended
    blindly: the adapter asks the durable-log scanner for exact matches and
    proceeds only when exactly one index is found. ASSIGNED rows only wait for
    publication. RECORDED rows replay the original receipt.
    """

    def __init__(
        self,
        outbox: SQLiteIdempotencyOutbox,
        tessera: TesseraClient,
    ) -> None:
        self._outbox = outbox
        self._tessera = tessera

    def submit(self, idempotency_key: str, leaf_hash: bytes) -> OutboxRecord:
        record = self._outbox.reserve(idempotency_key, leaf_hash)

        if record.state == "RECORDED":
            return record

        if record.state == "PENDING":
            if record.replayed:
                matches = self._tessera.find_entries(leaf_hash)
                if len(matches) != 1:
                    raise ReconciliationRequired(
                        "pending outbox row requires exactly one durable Tessera match; "
                        f"found {len(matches)}"
                    )
                tessera_index = matches[0]
            else:
                tessera_index = self._tessera.append(leaf_hash)

            record = self._outbox.assign(
                idempotency_key,
                leaf_hash,
                tessera_index=tessera_index,
            )

        if record.state != "ASSIGNED" or record.tessera_index is None:
            raise CorruptStoreError("outbox entered an unsupported state")

        checkpoint = self._tessera.wait_for_checkpoint(record.tessera_index)
        if (
            isinstance(checkpoint.tree_size, bool)
            or not isinstance(checkpoint.tree_size, int)
            or checkpoint.tree_size <= record.tessera_index
            or not isinstance(checkpoint.root_hash, bytes)
            or len(checkpoint.root_hash) != HASH_SIZE
            or not isinstance(checkpoint.checkpoint_note, bytes)
            or not checkpoint.checkpoint_note
        ):
            raise ReconciliationRequired(
                "Tessera has not provided a valid checkpoint covering the assigned index"
            )

        return self._outbox.record_checkpoint(
            idempotency_key,
            leaf_hash,
            tessera_index=record.tessera_index,
            tree_size=checkpoint.tree_size,
            root_hash=checkpoint.root_hash,
            checkpoint_note=checkpoint.checkpoint_note,
        )
