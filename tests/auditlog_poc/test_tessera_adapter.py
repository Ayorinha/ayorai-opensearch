"""Tests for the fail-closed Tessera outbox adapter contract."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ayorai_attractor.auditlog import inclusion_proof, tree_root
from experiments.adr010_poc.idempotency_outbox import SQLiteIdempotencyOutbox
from experiments.adr010_poc.python_writer import IdempotencyConflict
from experiments.adr010_poc.tessera_adapter import (
    ReconciliationRequired,
    TesseraOutboxAdapter,
    VerifiedCheckpoint,
)

LEAF = bytes.fromhex("6f4f7c6c6f5a4f0b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123")
OTHER_LEAF = bytes([LEAF[0] ^ 1]) + LEAF[1:]


class FakeTessera:
    def __init__(self) -> None:
        self.entries: list[bytes] = []
        self.checkpoint_override: VerifiedCheckpoint | None = None

    def append(self, leaf_hash: bytes) -> int:
        index = len(self.entries)
        self.entries.append(leaf_hash)
        return index

    def find_entries(self, leaf_hash: bytes) -> list[int]:
        return [index for index, entry in enumerate(self.entries) if entry == leaf_hash]

    def wait_for_checkpoint(self, tessera_index: int) -> VerifiedCheckpoint:
        if self.checkpoint_override is not None:
            return self.checkpoint_override
        tree_size = len(self.entries)
        if tree_size <= tessera_index:
            raise RuntimeError("fake checkpoint does not include assigned index")
        root_hash = tree_root(tuple(self.entries))
        note = f"verified-test-checkpoint:{tree_size}:{root_hash.hex()}".encode("ascii")
        proof = tuple(inclusion_proof(tessera_index, tuple(self.entries)))
        return VerifiedCheckpoint(tree_size, root_hash, note, proof)


def test_adapter_records_once_and_replays_original_receipt_after_restart(
    tmp_path: Path,
) -> None:
    database = tmp_path / "adapter-replay.sqlite3"
    outbox = SQLiteIdempotencyOutbox(database)
    tessera = FakeTessera()

    first = TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)
    replay = TesseraOutboxAdapter(SQLiteIdempotencyOutbox(database), tessera).submit(
        "request-1", LEAF
    )

    assert first.state == "RECORDED"
    assert first.tessera_index == 0
    assert replay.state == "RECORDED"
    assert replay.replayed
    assert replay.tessera_index == 0
    assert len(tessera.entries) == 1


def test_adapter_reconciles_pending_row_when_one_durable_match_exists(
    tmp_path: Path,
) -> None:
    database = tmp_path / "adapter-pending-reconcile.sqlite3"
    outbox = SQLiteIdempotencyOutbox(database)
    outbox.reserve("request-1", LEAF)

    tessera = FakeTessera()
    tessera.append(LEAF)  # Simulates Tessera accepted Add before the process crashed.
    record = TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    assert record.state == "RECORDED"
    assert record.tessera_index == 0
    assert len(tessera.entries) == 1


def test_adapter_resumes_assigned_row_without_appending_again(tmp_path: Path) -> None:
    database = tmp_path / "adapter-assigned-resume.sqlite3"
    outbox = SQLiteIdempotencyOutbox(database)
    outbox.reserve("request-1", LEAF)
    tessera = FakeTessera()
    index = tessera.append(LEAF)
    outbox.assign("request-1", LEAF, index)

    record = TesseraOutboxAdapter(
        SQLiteIdempotencyOutbox(database), tessera
    ).submit("request-1", LEAF)

    assert record.state == "RECORDED"
    assert record.tessera_index == 0
    assert len(tessera.entries) == 1


def test_adapter_fails_closed_when_pending_row_has_no_remote_match(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "adapter-no-match.sqlite3")
    outbox.reserve("request-1", LEAF)
    tessera = FakeTessera()

    with pytest.raises(ReconciliationRequired, match="found 0"):
        TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    assert tessera.entries == []
    assert outbox.get("request-1").state == "PENDING"


def test_adapter_fails_closed_when_pending_row_has_multiple_remote_matches(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "adapter-ambiguous.sqlite3")
    outbox.reserve("request-1", LEAF)
    tessera = FakeTessera()
    tessera.append(LEAF)
    tessera.append(LEAF)

    with pytest.raises(ReconciliationRequired, match="found 2"):
        TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    assert len(tessera.entries) == 2
    assert outbox.get("request-1").state == "PENDING"


def test_adapter_rejects_same_key_with_different_leaf_before_remote_append(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "adapter-conflict.sqlite3")
    tessera = FakeTessera()
    TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    with pytest.raises(IdempotencyConflict):
        TesseraOutboxAdapter(outbox, tessera).submit("request-1", OTHER_LEAF)

    assert len(tessera.entries) == 1


def test_adapter_keeps_assigned_state_when_checkpoint_is_not_valid(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "adapter-invalid-checkpoint.sqlite3")
    tessera = FakeTessera()
    tessera.checkpoint_override = VerifiedCheckpoint(
        tree_size=0,
        root_hash=b"short",
        checkpoint_note=b"unverified",
        inclusion_proof=(),
    )

    with pytest.raises(ReconciliationRequired, match="valid checkpoint"):
        TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    record = outbox.get("request-1")
    assert record is not None
    assert record.state == "ASSIGNED"
    assert record.tessera_index == 0


def test_adapter_parallel_replays_of_recorded_key_never_append_again(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "adapter-parallel-replay.sqlite3")
    tessera = FakeTessera()
    TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF)

    with ThreadPoolExecutor(max_workers=8) as executor:
        records = list(
            executor.map(
                lambda _: TesseraOutboxAdapter(outbox, tessera).submit("request-1", LEAF),
                range(16),
            )
        )

    assert all(record.state == "RECORDED" for record in records)
    assert len(tessera.entries) == 1
