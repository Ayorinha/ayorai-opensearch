"""Tests for the isolated ADR-010 SQLite writer experiment."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.auditlog import HASH_SIZE
from experiments.adr010_poc.python_writer import (
    CorruptStoreError,
    IdempotencyConflict,
    SQLiteMerkleWriter,
)

VECTOR_PATH = (
    Path(__file__).parents[1] / "auditlog" / "vectors" / "rfc6962-transparency-dev.json"
)
VECTORS = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
LEAF_HASHES = [bytes.fromhex(value) for value in VECTORS["leaf_hashes"]]
ROOTS = [bytes.fromhex(value) for value in VECTORS["roots"]]


def test_python_writer_reproduces_go_reference_roots_and_receipts(tmp_path: Path) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "writer.sqlite3")

    receipts = [
        writer.append(f"public-vector-{index}", leaf_hash)
        for index, leaf_hash in enumerate(LEAF_HASHES)
    ]

    assert len(receipts) == len(LEAF_HASHES) == 17
    for index, receipt in enumerate(receipts):
        assert receipt.index == index
        assert receipt.tree_size == index + 1
        assert receipt.root_hash == ROOTS[index + 1]
        assert writer.verify_receipt(receipt)

    head = writer.tree_head()
    assert head.tree_size == 17
    assert head.root_hash == ROOTS[17]
    assert writer.matches_checkpoint(17, ROOTS[17])


def test_idempotent_retry_returns_the_original_receipt(tmp_path: Path) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "retry.sqlite3")
    first = writer.append("retry-key", LEAF_HASHES[0])
    writer.append("later-key", LEAF_HASHES[1])

    retry = writer.append("retry-key", LEAF_HASHES[0])

    assert retry.duplicate
    assert retry.index == first.index
    assert retry.tree_size == first.tree_size
    assert retry.leaf_hash == first.leaf_hash
    assert retry.root_hash == first.root_hash
    assert writer.tree_head().tree_size == 2


def test_idempotency_key_cannot_be_reused_for_another_leaf(tmp_path: Path) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "conflict.sqlite3")
    writer.append("same-key", LEAF_HASHES[0])

    with pytest.raises(IdempotencyConflict):
        writer.append("same-key", LEAF_HASHES[1])

    assert writer.tree_head().tree_size == 1


def test_restart_preserves_tree_head_and_verifiable_receipts(tmp_path: Path) -> None:
    database = tmp_path / "restart.sqlite3"
    first_writer = SQLiteMerkleWriter(database)
    receipts = [
        first_writer.append(f"restart-{index}", leaf_hash)
        for index, leaf_hash in enumerate(LEAF_HASHES[:8])
    ]
    expected_head = first_writer.tree_head()

    restarted_writer = SQLiteMerkleWriter(database)

    assert restarted_writer.tree_head() == expected_head
    assert all(restarted_writer.verify_receipt(receipt) for receipt in receipts)


def test_mutated_leaf_no_longer_matches_a_caller_held_checkpoint(tmp_path: Path) -> None:
    database = tmp_path / "mutation.sqlite3"
    writer = SQLiteMerkleWriter(database)
    receipt = writer.append("mutation-key", LEAF_HASHES[0])
    checkpoint = writer.tree_head()

    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            UPDATE adr010_poc_entries
            SET leaf_hash = ?
            WHERE leaf_index = 0
            """,
            (bytes([LEAF_HASHES[0][0] ^ 1]) + LEAF_HASHES[0][1:],),
        )
        connection.commit()

    reopened = SQLiteMerkleWriter(database)
    assert not reopened.matches_checkpoint(checkpoint.tree_size, checkpoint.root_hash)
    assert not reopened.verify_receipt(receipt)


def test_deleted_entry_is_detected_without_silent_repair(tmp_path: Path) -> None:
    database = tmp_path / "deletion.sqlite3"
    writer = SQLiteMerkleWriter(database)
    for index, leaf_hash in enumerate(LEAF_HASHES[:3]):
        writer.append(f"delete-{index}", leaf_hash)

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DELETE FROM adr010_poc_entries WHERE leaf_index = 1")
        connection.commit()

    with pytest.raises(CorruptStoreError, match="entry count"):
        SQLiteMerkleWriter(database)



def test_process_crash_before_commit_does_not_leave_partial_entry(tmp_path: Path) -> None:
    database = tmp_path / "crash-recovery.sqlite3"
    SQLiteMerkleWriter(database)
    child_code = """
import os
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    "INSERT INTO adr010_poc_entries "
    "(leaf_index, idempotency_key, leaf_hash, tree_size_at_append, root_hash_at_append) "
    "VALUES (0, 'crash-before-commit', ?, 1, ?)",
    (bytes(32), bytes(32)),
)
os._exit(23)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", child_code, str(database)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert crashed.returncode == 23
    recovered = SQLiteMerkleWriter(database)
    assert recovered.tree_head().tree_size == 0
    assert recovered.matches_checkpoint(0, recovered.tree_head().root_hash)


def test_concurrent_appends_are_serialized_without_lost_indices(tmp_path: Path) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "concurrent.sqlite3")
    work = [
        (f"concurrent-{index}", leaf_hash)
        for index, leaf_hash in enumerate(LEAF_HASHES)
    ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = list(executor.map(lambda item: writer.append(*item), work))

    assert sorted(receipt.index for receipt in receipts) == list(range(len(work)))
    assert writer.tree_head().tree_size == len(work)
    assert all(writer.verify_receipt(receipt) for receipt in receipts)


def test_concurrent_duplicate_retries_create_only_one_entry(tmp_path: Path) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "duplicate-race.sqlite3")

    with ThreadPoolExecutor(max_workers=6) as executor:
        receipts = list(
            executor.map(
                lambda _: writer.append("same-retry", LEAF_HASHES[0]),
                range(12),
            )
        )

    assert writer.tree_head().tree_size == 1
    assert {receipt.index for receipt in receipts} == {0}
    assert sum(not receipt.duplicate for receipt in receipts) == 1
    assert all(writer.verify_receipt(receipt) for receipt in receipts)


@pytest.mark.parametrize(
    ("key", "leaf_hash"),
    [
        ("", bytes(HASH_SIZE)),
        ("   ", bytes(HASH_SIZE)),
        ("x" * 257, bytes(HASH_SIZE)),
        ("valid", b"short"),
    ],
)
def test_invalid_append_inputs_are_rejected(
    tmp_path: Path, key: str, leaf_hash: bytes
) -> None:
    writer = SQLiteMerkleWriter(tmp_path / "invalid.sqlite3")

    with pytest.raises(ValueError):
        writer.append(key, leaf_hash)

    assert writer.tree_head().tree_size == 0
