"""Tests for the incremental SQLite Merkle-frontier prototype."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest

from experiments.adr010_poc.frontier_writer import (
    MerkleFrontier,
    SQLiteFrontierWriter,
)
from experiments.adr010_poc.python_writer import CorruptStoreError, IdempotencyConflict

VECTOR_PATH = Path(__file__).parents[1] / "auditlog" / "vectors" / "rfc6962-transparency-dev.json"
VECTORS = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
LEAF_HASHES = [bytes.fromhex(value) for value in VECTORS["leaf_hashes"]]
ROOTS = [bytes.fromhex(value) for value in VECTORS["roots"]]


def test_frontier_accumulator_reproduces_every_public_reference_root() -> None:
    frontier = MerkleFrontier()

    for index, leaf_hash in enumerate(LEAF_HASHES):
        assert frontier.append(leaf_hash) == ROOTS[index + 1]
        assert frontier.tree_size == index + 1


def test_sqlite_frontier_writer_reproduces_roots_and_historical_checkpoints(
    tmp_path: Path,
) -> None:
    writer = SQLiteFrontierWriter(tmp_path / "frontier.sqlite3")
    receipts = [
        writer.append(f"frontier-{index}", leaf_hash) for index, leaf_hash in enumerate(LEAF_HASHES)
    ]

    for index, receipt in enumerate(receipts):
        assert receipt.index == index
        assert receipt.tree_size == index + 1
        assert receipt.root_hash == ROOTS[index + 1]
        assert writer.verify_receipt(receipt)
        assert writer.matches_checkpoint(index + 1, ROOTS[index + 1])

    assert writer.matches_checkpoint(0, ROOTS[0])
    assert writer.tree_head().root_hash == ROOTS[17]


def test_frontier_writer_rebuilds_and_checks_state_after_restart(tmp_path: Path) -> None:
    database = tmp_path / "frontier-restart.sqlite3"
    first = SQLiteFrontierWriter(database)
    receipts = [
        first.append(f"restart-{index}", leaf_hash)
        for index, leaf_hash in enumerate(LEAF_HASHES[:9])
    ]

    restarted = SQLiteFrontierWriter(database)

    assert restarted.tree_head().tree_size == 9
    assert restarted.tree_head().root_hash == ROOTS[9]
    assert all(restarted.verify_receipt(receipt) for receipt in receipts)


def test_frontier_writer_returns_original_receipt_for_same_idempotency_key(
    tmp_path: Path,
) -> None:
    writer = SQLiteFrontierWriter(tmp_path / "frontier-retry.sqlite3")
    first = writer.append("same-key", LEAF_HASHES[0])
    writer.append("later-key", LEAF_HASHES[1])

    retry = writer.append("same-key", LEAF_HASHES[0])

    assert retry.duplicate
    assert retry.index == first.index
    assert retry.tree_size == first.tree_size
    assert retry.root_hash == first.root_hash
    assert writer.tree_head().tree_size == 2


def test_frontier_writer_rejects_idempotency_key_with_different_leaf(
    tmp_path: Path,
) -> None:
    writer = SQLiteFrontierWriter(tmp_path / "frontier-conflict.sqlite3")
    writer.append("same-key", LEAF_HASHES[0])

    with pytest.raises(IdempotencyConflict):
        writer.append("same-key", LEAF_HASHES[1])

    assert writer.tree_head().tree_size == 1


def test_frontier_writer_serializes_concurrent_appends(tmp_path: Path) -> None:
    writer = SQLiteFrontierWriter(tmp_path / "frontier-concurrent.sqlite3")
    work = [(f"frontier-concurrent-{index}", leaf) for index, leaf in enumerate(LEAF_HASHES)]

    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = list(executor.map(lambda item: writer.append(*item), work))

    assert sorted(receipt.index for receipt in receipts) == list(range(len(work)))
    assert writer.tree_head().tree_size == len(work)
    assert all(writer.verify_receipt(receipt) for receipt in receipts)


def test_frontier_writer_detects_leaf_mutation_on_restart(tmp_path: Path) -> None:
    database = tmp_path / "frontier-mutation.sqlite3"
    SQLiteFrontierWriter(database).append("mutation", LEAF_HASHES[0])

    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            UPDATE adr010_frontier_entries
            SET leaf_hash = ?
            WHERE leaf_index = 0
            """,
            (bytes([LEAF_HASHES[0][0] ^ 1]) + LEAF_HASHES[0][1:],),
        )
        connection.commit()

    with pytest.raises(CorruptStoreError, match="frontier"):
        SQLiteFrontierWriter(database)


def test_external_checkpoint_detects_consistent_local_rewrite(tmp_path: Path) -> None:
    database = tmp_path / "frontier-external-anchor.sqlite3"
    writer = SQLiteFrontierWriter(database)
    receipt = writer.append("anchored", LEAF_HASHES[0])
    checkpoint = writer.tree_head()
    changed_leaf = bytes([LEAF_HASHES[0][0] ^ 1]) + LEAF_HASHES[0][1:]

    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            """
            UPDATE adr010_frontier_entries
            SET leaf_hash = ?, root_hash_at_append = ?
            WHERE leaf_index = 0
            """,
            (changed_leaf, changed_leaf),
        )
        connection.execute(
            """
            UPDATE adr010_frontier_nodes
            SET node_hash = ?
            WHERE level = 0
            """,
            (changed_leaf,),
        )
        connection.commit()

    rewritten = SQLiteFrontierWriter(database)
    assert not rewritten.matches_checkpoint(checkpoint.tree_size, checkpoint.root_hash)
    assert not rewritten.verify_receipt(receipt)


def test_frontier_writer_detects_deleted_entry_on_restart(tmp_path: Path) -> None:
    database = tmp_path / "frontier-deletion.sqlite3"
    SQLiteFrontierWriter(database).append("keep", LEAF_HASHES[0])

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("DELETE FROM adr010_frontier_entries WHERE leaf_index = 0")
        connection.commit()

    with pytest.raises(CorruptStoreError, match="entry count"):
        SQLiteFrontierWriter(database)


def test_frontier_writer_recovers_uncommitted_transaction_after_process_exit(
    tmp_path: Path,
) -> None:
    database = tmp_path / "frontier-crash.sqlite3"
    SQLiteFrontierWriter(database)
    child_code = """
import os
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    "INSERT INTO adr010_frontier_entries "
    "(leaf_index, idempotency_key, leaf_hash, tree_size_at_append, root_hash_at_append) "
    "VALUES (0, 'crash-before-commit', ?, 1, ?)",
    (bytes(32), bytes(32)),
)
connection.execute(
    "UPDATE adr010_frontier_metadata SET tree_size = 1 WHERE singleton = 1"
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
    recovered = SQLiteFrontierWriter(database)
    assert recovered.tree_head().tree_size == 0


def test_frontier_writer_retry_recovers_after_commit_before_response_loss(
    tmp_path: Path,
) -> None:
    database = tmp_path / "frontier-lost-response.sqlite3"
    leaf_hex = LEAF_HASHES[0].hex()
    child_code = f"""
import os
import sys
from experiments.adr010_poc.frontier_writer import SQLiteFrontierWriter

writer = SQLiteFrontierWriter(sys.argv[1])
writer.append("committed-response-lost", bytes.fromhex({leaf_hex!r}))
os._exit(23)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", child_code, str(database)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert crashed.returncode == 23
    writer = SQLiteFrontierWriter(database)
    retry = writer.append("committed-response-lost", LEAF_HASHES[0])

    assert retry.duplicate
    assert retry.index == 0
    assert retry.tree_size == 1
    assert writer.tree_head().tree_size == 1
    assert writer.verify_receipt(retry)
