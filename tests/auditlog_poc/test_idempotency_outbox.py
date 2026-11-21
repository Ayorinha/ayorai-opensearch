"""Tests for the durable Tessera idempotency outbox state machine."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ayorai_attractor.auditlog import inclusion_proof, tree_root
from experiments.adr010_poc.idempotency_outbox import SQLiteIdempotencyOutbox
from experiments.adr010_poc.python_writer import CorruptStoreError, IdempotencyConflict

LEAF = bytes.fromhex(
    "6f4f7c6c6f5a4f0b2c3d4e5f60718293"
    "a4b5c6d7e8f90123456789abcdef0123"
)
OTHER_LEAF = bytes([LEAF[0] ^ 1]) + LEAF[1:]
ROOT = LEAF
SIGNED_CHECKPOINT = b"test-only signed checkpoint note"


def test_outbox_transitions_pending_assigned_recorded_and_replays(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox.sqlite3")

    pending = outbox.reserve("request-1", LEAF)
    assigned = outbox.assign("request-1", LEAF, tessera_index=0)
    recorded = outbox.record_checkpoint(
        "request-1",
        LEAF,
        tessera_index=0,
        tree_size=1,
        root_hash=ROOT,
        checkpoint_note=SIGNED_CHECKPOINT,
        inclusion_proof=(),
    )
    replay = outbox.reserve("request-1", LEAF)

    assert pending.state == "PENDING"
    assert assigned.state == "ASSIGNED"
    assert recorded.state == "RECORDED"
    assert recorded.tessera_index == 0
    assert recorded.tree_size == 1
    assert recorded.root_hash == ROOT
    assert recorded.checkpoint_note == SIGNED_CHECKPOINT
    assert replay.replayed
    assert replay.state == "RECORDED"
    assert replay.tessera_index == 0
    assert outbox.list_unresolved() == ()


def test_outbox_rejects_same_key_with_different_leaf_commitment(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-conflict.sqlite3")
    outbox.reserve("request-1", LEAF)

    with pytest.raises(IdempotencyConflict):
        outbox.reserve("request-1", OTHER_LEAF)


def test_outbox_assign_is_idempotent_but_rejects_different_index(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-assign.sqlite3")
    outbox.reserve("request-1", LEAF)

    first = outbox.assign("request-1", LEAF, tessera_index=7)
    replay = outbox.assign("request-1", LEAF, tessera_index=7)

    assert first.state == "ASSIGNED"
    assert not first.replayed
    assert replay.state == "ASSIGNED"
    assert replay.replayed
    with pytest.raises(CorruptStoreError, match="different index"):
        outbox.assign("request-1", LEAF, tessera_index=8)


def test_outbox_prevents_two_idempotency_keys_from_claiming_one_tessera_index(
    tmp_path: Path,
) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-unique-index.sqlite3")
    outbox.reserve("request-a", LEAF)
    outbox.reserve("request-b", OTHER_LEAF)
    outbox.assign("request-a", LEAF, tessera_index=0)

    with pytest.raises(CorruptStoreError, match="already assigned"):
        outbox.assign("request-b", OTHER_LEAF, tessera_index=0)


def test_outbox_record_checkpoint_is_idempotent_and_immutable(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-record.sqlite3")
    outbox.reserve("request-1", LEAF)
    outbox.assign("request-1", LEAF, tessera_index=0)

    first = outbox.record_checkpoint(
        "request-1", LEAF, 0, 1, ROOT, SIGNED_CHECKPOINT, ()
    )
    replay = outbox.record_checkpoint(
        "request-1", LEAF, 0, 1, ROOT, SIGNED_CHECKPOINT, ()
    )

    assert first.state == "RECORDED"
    assert not first.replayed
    assert replay.state == "RECORDED"
    assert replay.replayed
    with pytest.raises(CorruptStoreError, match="silently replaced"):
        outbox.record_checkpoint(
            "request-1", LEAF, 0, 1, ROOT, b"different checkpoint", ()
        )


def test_pending_outbox_survives_restart_and_fails_closed_until_reconciled(
    tmp_path: Path,
) -> None:
    database = tmp_path / "outbox-pending-restart.sqlite3"
    SQLiteIdempotencyOutbox(database).reserve("request-1", LEAF)

    restarted = SQLiteIdempotencyOutbox(database)
    replay = restarted.reserve("request-1", LEAF)

    assert replay.replayed
    assert replay.state == "PENDING"
    assert replay.tessera_index is None
    assert [row.idempotency_key for row in restarted.list_unresolved()] == ["request-1"]

    pending_leaves = (OTHER_LEAF, OTHER_LEAF, OTHER_LEAF, OTHER_LEAF, LEAF)
    pending_root = tree_root(pending_leaves)
    pending_proof = tuple(inclusion_proof(4, pending_leaves))
    reconciled = restarted.record_checkpoint(
        "request-1",
        LEAF,
        tessera_index=4,
        tree_size=5,
        root_hash=pending_root,
        checkpoint_note=SIGNED_CHECKPOINT,
        inclusion_proof=pending_proof,
    )
    assert reconciled.state == "RECORDED"
    assert reconciled.tessera_index == 4


def test_assigned_outbox_survives_restart_until_checkpoint_is_published(
    tmp_path: Path,
) -> None:
    database = tmp_path / "outbox-assigned-restart.sqlite3"
    first = SQLiteIdempotencyOutbox(database)
    first.reserve("request-1", LEAF)
    first.assign("request-1", LEAF, tessera_index=3)

    restarted = SQLiteIdempotencyOutbox(database)
    unresolved = restarted.list_unresolved()

    assert len(unresolved) == 1
    assert unresolved[0].state == "ASSIGNED"
    assert unresolved[0].tessera_index == 3

    assigned_leaves = (OTHER_LEAF, OTHER_LEAF, OTHER_LEAF, LEAF)
    assigned_root = tree_root(assigned_leaves)
    assigned_proof = tuple(inclusion_proof(3, assigned_leaves))
    recorded = restarted.record_checkpoint(
        "request-1",
        LEAF,
        tessera_index=3,
        tree_size=4,
        root_hash=assigned_root,
        checkpoint_note=SIGNED_CHECKPOINT,
        inclusion_proof=assigned_proof,
    )
    assert recorded.state == "RECORDED"


def test_outbox_concurrent_reservations_create_one_pending_operation(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-concurrent.sqlite3")

    with ThreadPoolExecutor(max_workers=8) as executor:
        records = list(executor.map(lambda _: outbox.reserve("same-key", LEAF), range(16)))

    assert sum(not record.replayed for record in records) == 1
    assert all(record.state == "PENDING" for record in records)
    assert len(outbox.list_unresolved()) == 1


def test_outbox_process_exit_after_reservation_preserves_pending_state(tmp_path: Path) -> None:
    database = tmp_path / "outbox-crash-pending.sqlite3"
    child_code = """
import os
import sys
from experiments.adr010_poc.idempotency_outbox import SQLiteIdempotencyOutbox

outbox = SQLiteIdempotencyOutbox(sys.argv[1])
outbox.reserve("crash-pending", bytes.fromhex(sys.argv[2]))
os._exit(23)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", child_code, str(database), LEAF.hex()],
        check=False,
        capture_output=True,
        text=True,
    )

    assert crashed.returncode == 23
    recovered = SQLiteIdempotencyOutbox(database)
    record = recovered.get("crash-pending")
    assert record is not None
    assert record.state == "PENDING"


def test_outbox_process_exit_after_assignment_preserves_index(tmp_path: Path) -> None:
    database = tmp_path / "outbox-crash-assigned.sqlite3"
    child_code = """
import os
import sys
from experiments.adr010_poc.idempotency_outbox import SQLiteIdempotencyOutbox

outbox = SQLiteIdempotencyOutbox(sys.argv[1])
outbox.reserve("crash-assigned", bytes.fromhex(sys.argv[2]))
outbox.assign("crash-assigned", bytes.fromhex(sys.argv[2]), 12)
os._exit(23)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", child_code, str(database), LEAF.hex()],
        check=False,
        capture_output=True,
        text=True,
    )

    assert crashed.returncode == 23
    recovered = SQLiteIdempotencyOutbox(database)
    record = recovered.get("crash-assigned")
    assert record is not None
    assert record.state == "ASSIGNED"
    assert record.tessera_index == 12


def test_outbox_rejects_invalid_checkpoint_metadata(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-invalid.sqlite3")
    outbox.reserve("request-1", LEAF)

    with pytest.raises(ValueError, match="tree_size"):
        outbox.record_checkpoint(
            "request-1", LEAF, 0, 0, ROOT, SIGNED_CHECKPOINT, ()
        )
    with pytest.raises(ValueError, match="root_hash"):
        outbox.record_checkpoint(
            "request-1", LEAF, 0, 1, b"short", SIGNED_CHECKPOINT, ()
        )
    with pytest.raises(ValueError, match="checkpoint_note"):
        outbox.record_checkpoint("request-1", LEAF, 0, 1, ROOT, b"", ())


def test_outbox_rejects_assign_or_record_without_reservation(tmp_path: Path) -> None:
    outbox = SQLiteIdempotencyOutbox(tmp_path / "outbox-missing.sqlite3")

    with pytest.raises(CorruptStoreError, match="unreserved"):
        outbox.assign("missing", LEAF, tessera_index=0)
    with pytest.raises(CorruptStoreError, match="unreserved"):
        outbox.record_checkpoint(
            "missing", LEAF, 0, 1, ROOT, SIGNED_CHECKPOINT, ()
        )
