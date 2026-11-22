"""ADR-010: integrity checks of the verify log while it is open, and rejection paths.

``test_verify_log.py`` tampers with a closed database, which is caught when the
tree is reloaded. Here the database is changed by another connection while the
log stays open, which is what ``verify_log()`` exists to catch on a running
service, and every problem it reports is checked by name.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from ayorai_attractor.auditlog.merkle import inclusion_proof, leaf_hash
from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationEvent, VerificationLog, verify_receipt
from tests.test_verify_log import ORIGIN, SEED, _event


@pytest.fixture
def open_log(tmp_path: Path) -> Iterator[tuple[VerificationLog, str]]:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        for n in range(3):
            store.append(_event(n))
        yield store, path


def _sql(path: str, statement: str, params: tuple[Any, ...] = ()) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement, params)
        connection.commit()


def _problems(store: VerificationLog) -> list[str]:
    report = store.verify_log()
    assert report["valid"] is False
    return list(report["problems"])


# --- live tampering: each problem is named -------------------------------------


def test_fresh_log_is_valid(open_log: tuple[VerificationLog, str]) -> None:
    store, _ = open_log
    report = store.verify_log()
    assert report == {
        "valid": True,
        "size": 3,
        "checkpoints": 3,
        "erased_records": 0,
        "problems": [],
    }


def test_changed_leaf_with_stale_hash_is_reported(open_log: tuple[VerificationLog, str]) -> None:
    store, path = open_log
    _sql(path, "UPDATE vlog_leaves SET leaf = X'7b7d' WHERE idx = 1")
    assert "leaf 1 hash mismatch" in _problems(store)

def test_record_mutation_is_detected_against_the_leaf_commitment(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    _sql(path, "UPDATE vlog_records SET record = ? WHERE idx = 1", ('{"verdict":"SUPPORTED"}',))
    assert "record 1 commitment mismatch" in _problems(store)


def test_salt_mutation_is_detected_against_the_leaf_commitment(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    _sql(path, "UPDATE vlog_records SET salt = X'00' WHERE idx = 1")
    assert "record 1 commitment mismatch" in _problems(store)


def test_partial_record_erasure_is_reported(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    _sql(path, "UPDATE vlog_records SET salt = NULL WHERE idx = 1")
    assert "record 1 is incomplete or partially erased" in _problems(store)


def test_orphan_record_row_is_reported(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    _sql(
        path,
        "INSERT INTO vlog_records (idx, salt, record, erased_at) VALUES (99, X'00', '{}', NULL)",
    )
    assert "record 99 has no event leaf" in _problems(store)


def test_erasure_leaf_cannot_target_another_erasure_leaf(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0))
        store.erase(0, "2026-11-22T00:00:00Z")
        store.append(_event(1))
        store.erase(2, "2026-11-22T00:00:00Z")
        erasure = json.dumps(
            {
                "schema": "ayorai.verify-erasure.v1",
                "erased_index": 1,
                "erased_at": "2026-11-22T00:00:00Z",
                "reason": "data_subject_request",
            }
        ).encode()
        _sql(
            path,
            "UPDATE vlog_leaves SET leaf = ?, leaf_hash = ? WHERE idx = 3",
            (erasure, leaf_hash(erasure)),
        )
        problems = _problems(store)
    assert "erasure leaf 3 names an invalid event" in problems
    assert "record 2 erased without an erasure event" in problems


def test_changed_leaf_with_recomputed_hash_breaks_the_signed_roots(
    open_log: tuple[VerificationLog, str],
) -> None:
    # A writer without the signing key recomputes the leaf hash: the stored
    # checkpoints no longer match the tree.
    store, path = open_log
    forged = b'{"forged":true}'
    _sql(
        path,
        "UPDATE vlog_leaves SET leaf = ?, leaf_hash = ? WHERE idx = 1",
        (forged, leaf_hash(forged)),
    )
    problems = _problems(store)
    assert "checkpoint 2: root does not match the tree" in problems
    assert "checkpoint 3: root does not match the tree" in problems
    assert "leaf 1 is not JSON" not in problems


def test_a_gap_in_the_leaves_is_reported(open_log: tuple[VerificationLog, str]) -> None:
    store, path = open_log
    _sql(path, "UPDATE vlog_leaves SET idx = 7 WHERE idx = 2")
    assert "gap before leaf 7" in _problems(store)


def test_a_leaf_that_is_not_json_is_reported(open_log: tuple[VerificationLog, str]) -> None:
    store, path = open_log
    garbage = b"\xff\xfe not json"
    _sql(
        path,
        "UPDATE vlog_leaves SET leaf = ?, leaf_hash = ? WHERE idx = 0",
        (garbage, leaf_hash(garbage)),
    )
    assert "leaf 0 is not JSON" in _problems(store)

def test_an_unknown_public_leaf_schema_is_reported(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    unknown = b'{"schema":"ayorai.unknown.v1"}'
    _sql(
        path,
        "UPDATE vlog_leaves SET leaf = ?, leaf_hash = ? WHERE idx = 1",
        (unknown, leaf_hash(unknown)),
    )
    problems = _problems(store)
    assert "leaf 1 has an unknown schema" in problems
    assert "record 1 has no event leaf" in problems



@pytest.mark.parametrize("target", [5, -1, "0", None])
def test_an_erasure_leaf_naming_an_invalid_event_is_reported(
    tmp_path: Path, target: object
) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0))
        erasure = store.erase(0, "2026-11-22T00:00:00Z")
        assert erasure == 1
        leaf = json.dumps(
            {
                "schema": "ayorai.verify-erasure.v1",
                "erased_index": target,
                "erased_at": "2026-11-22T00:00:00Z",
                "reason": "data_subject_request",
            }
        ).encode()
        _sql(
            path,
            "UPDATE vlog_leaves SET leaf = ?, leaf_hash = ? WHERE idx = 1",
            (leaf, leaf_hash(leaf)),
        )
        problems = _problems(store)
    assert "erasure leaf 1 names an invalid event" in problems
    assert "record 0 erased without an erasure event" in problems


def test_a_checkpoint_signed_by_another_key_is_reported(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, path = open_log
    foreign = NoteSigner(ORIGIN, bytes(32)).sign(f"{ORIGIN}\n2\n{'A' * 43}=\n")
    _sql(path, "UPDATE vlog_checkpoints SET note = ? WHERE size = 2", (foreign,))
    assert "checkpoint 2: bad signature or body" in _problems(store)


# --- erasure is atomic -----------------------------------------------------------


def test_a_failed_erasure_changes_nothing(
    open_log: tuple[VerificationLog, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _ = open_log
    receipt_size = store.size()

    def broken_sign(body: str) -> str:
        raise OSError("signing service unavailable")

    monkeypatch.setattr(store.signer, "sign", broken_sign)
    with pytest.raises(OSError):
        store.erase(1, "2026-11-22T00:00:00Z")
    monkeypatch.undo()
    assert store.size() == receipt_size
    report = store.verify_log()
    assert report["valid"] is True and report["erased_records"] == 0
    # The record is still there and can be erased once signing works again.
    assert store.erase(1, "2026-11-22T00:00:00Z") == receipt_size


def test_erasure_after_another_writer_appended_uses_the_current_tree(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with (
        VerificationLog(path, NoteSigner(ORIGIN, SEED)) as first,
        VerificationLog(path, NoteSigner(ORIGIN, SEED)) as second,
    ):
        first.append(_event(0))
        second.append(_event(1))  # first's in-memory tree is now one leaf behind
        assert first.erase(0, "2026-11-22T00:00:00Z") == 2
        assert first.verify_log()["valid"] is True
        assert second.verify_log()["valid"] is True


@pytest.mark.parametrize("reason", ["", "Has Upper", "x" * 65, "spaces here", "acentuação"])
def test_erasure_reason_must_be_a_short_code(
    open_log: tuple[VerificationLog, str], reason: str
) -> None:
    store, _ = open_log
    with pytest.raises(ValueError, match="reason"):
        store.erase(0, "2026-11-22T00:00:00Z", reason)


# --- argument validation ---------------------------------------------------------


@pytest.mark.parametrize("old_size", [0, -1, 4])
def test_consistency_rejects_sizes_outside_the_tree(
    open_log: tuple[VerificationLog, str], old_size: int
) -> None:
    store, _ = open_log
    with pytest.raises(ValueError, match="old_size"):
        store.consistency(old_size)


def test_empty_log_publishes_a_signed_size_zero_checkpoint(tmp_path: Path) -> None:
    with VerificationLog(str(tmp_path / "v.sqlite3"), NoteSigner(ORIGIN, SEED)) as store:
        note = store.latest_checkpoint()
        assert store.matches_checkpoint(note)
        assert f"{ORIGIN}\n0\n" in note


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("input_sha256", "ABC", "input_sha256"),
        ("output_sha256", "0" * 63, "output_sha256"),
        ("rules_sha256", "g" * 64, "rules_sha256"),
        ("decision_state", "", "required"),
        ("client", "", "required"),
        ("software_id", "", "required"),
    ],
)
def test_events_with_invalid_fields_are_refused(field: str, value: str, message: str) -> None:
    fields = {
        "input_sha256": "0" * 64,
        "output_sha256": "1" * 64,
        "rules_sha256": "a" * 64,
        "decision_state": "DECIDED",
        "verdict": "SUPPORTED",
        "client": "c",
        "received_at": "2026-11-22T00:00:00Z",
        "software_id": "x",
        field: value,
    }
    with pytest.raises(ValueError, match=message):
        VerificationEvent(**fields)


# --- receipts that must not verify -----------------------------------------------


def test_receipts_for_erasure_leaves_or_with_bad_index_types_do_not_verify(
    open_log: tuple[VerificationLog, str],
) -> None:
    store, _ = open_log
    receipt = store.append(_event(9))
    vkey = store.verifier_key
    assert verify_receipt(receipt, vkey)
    assert not verify_receipt({**receipt, "index": True}, vkey)  # bool is not an index
    assert not verify_receipt({**receipt, "index": "3"}, vkey)
    assert not verify_receipt({**receipt, "receipt_version": "v0"}, vkey)
    assert not verify_receipt({**receipt, "record": "not a mapping"}, vkey)
    assert not verify_receipt({**receipt, "salt": "!!"}, vkey)
    missing = dict(receipt)
    del missing["leaf"]
    assert not verify_receipt(missing, vkey)
    # A genuine erasure leaf, with a genuine inclusion proof, is not an event receipt.
    erasure_index = store.erase(receipt["index"], "2026-11-22T00:00:00Z")
    assert erasure_index is not None
    with closing(sqlite3.connect(store.path)) as connection:
        leaves = [
            bytes(row[0]) for row in connection.execute("SELECT leaf FROM vlog_leaves ORDER BY idx")
        ]
    leaf = leaves[erasure_index]
    forged = {
        **receipt,
        "index": erasure_index,
        "leaf": base64.b64encode(bytes(leaf)).decode(),
        "inclusion_proof": [
            base64.b64encode(node).decode()
            for node in inclusion_proof(erasure_index, [leaf_hash(x) for x in leaves])
        ],
        "checkpoint": store.latest_checkpoint(),
    }
    assert not verify_receipt(forged, vkey)
