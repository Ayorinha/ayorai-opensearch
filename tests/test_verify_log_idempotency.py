"""ADR-010: integrity of the idempotency table of the verify log.

A retry with the same ``Idempotency-Key`` returns the receipt stored for the first
request. That receipt lives in a mutable table outside the signed tree, so it is
checked before it is returned (same event, same leaf, valid signature, inclusion and
commitment, same input) and audited by ``verify_log()``. After an LGPD erasure the
stored receipt is redacted with the record, and a retry is refused.

The table is changed by another connection while the log stays open, which is the
threat model of ``verify_log()``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import (
    IdempotencyConflict,
    IdempotencyErased,
    LogCorruption,
    VerificationLog,
    verify_receipt,
)
from tests.test_verify_log import ORIGIN, SEED, _event

CLIENT = "client-a"
_INSERT = (
    "INSERT INTO vlog_idempotency (key_digest, input_sha256, idx, receipt) VALUES (?, ?, ?, ?)"
)


def _digest(key: str, client: str = CLIENT) -> str:
    return hashlib.sha256(f"{client}\x00{key}".encode()).hexdigest()


def _sql(path: str, statement: str, params: tuple[Any, ...] = ()) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement, params)
        connection.commit()


def _row(path: str, key: str) -> tuple[str, int, str]:
    with closing(sqlite3.connect(path)) as connection:
        row = connection.execute(
            "SELECT input_sha256, idx, receipt FROM vlog_idempotency WHERE key_digest = ?",
            (_digest(key),),
        ).fetchone()
    assert row is not None
    return str(row[0]), int(row[1]), str(row[2])


def _problems(store: VerificationLog) -> list[str]:
    report = store.verify_log()
    assert report["valid"] is False
    return list(report["problems"])


def _has(problems: list[str], fragment: str) -> bool:
    return any(fragment in problem for problem in problems)


def _verdict(n: int) -> str:
    return "REFUTED" if n % 2 == 0 else "SUPPORTED"


@pytest.fixture
def keyed_log(tmp_path: Path) -> Iterator[tuple[VerificationLog, str]]:
    """Four events, each sent with key ``k-<n>``; verdicts alternate."""
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        for n in range(4):
            store.append(_event(n, verdict=_verdict(n)), idempotency_key=f"k-{n}")
        yield store, path


def _assert_retry_refused(store: VerificationLog, n: int, error: type[Exception]) -> None:
    """A retry of event ``n`` with key ``k-<n>`` is refused and appends nothing."""
    size = store.size()
    with pytest.raises(error):
        store.append(_event(n, verdict=_verdict(n)), idempotency_key=f"k-{n}")
    assert store.size() == size


def test_untampered_keyed_log_is_valid_and_retries_return_the_stored_receipt(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    store, path = keyed_log
    assert store.verify_log()["valid"] is True
    again = store.append(_event(2, verdict="REFUTED"), idempotency_key="k-2")
    assert again == json.loads(_row(path, "k-2")[2])
    assert again["index"] == 2 and again["record"]["verdict"] == "REFUTED"
    assert store.size() == 4


# --- M1: the 12 required cases ---------------------------------------------------


def test_m1_01_receipts_swapped_between_events(keyed_log: tuple[VerificationLog, str]) -> None:
    """Receipt of event 1 stored under the row of event 0 (and vice versa)."""
    store, path = keyed_log
    _, _, receipt_0 = _row(path, "k-0")
    _, _, receipt_1 = _row(path, "k-1")
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (receipt_1, _digest("k-0")),
    )
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (receipt_0, _digest("k-1")),
    )
    problems = _problems(store)
    assert _has(problems, "receipt names event 1, row names 0")
    assert _has(problems, "receipt names event 0, row names 1")
    assert _has(problems, "receipt record input differs from the request input")
    # Before the fix, this retry returned event 1 (SUPPORTED) for a REFUTED request.
    _assert_retry_refused(store, 0, LogCorruption)
    _assert_retry_refused(store, 1, LogCorruption)


def test_m1_02_rows_swapped_between_requests(keyed_log: tuple[VerificationLog, str]) -> None:
    """Whole rows (input, index, receipt) exchanged between two keys.

    Each row stays self-consistent, and the key-to-event binding is not part of the
    signed tree, so ``verify_log()`` cannot see this (documented limitation). The
    retry still never serves the other request's receipt: its input differs.
    """
    store, path = keyed_log
    row_0 = _row(path, "k-0")
    row_1 = _row(path, "k-1")
    for key, row in (("k-0", row_1), ("k-1", row_0)):
        _sql(
            path,
            "UPDATE vlog_idempotency SET input_sha256 = ?, idx = ?, receipt = ? "
            "WHERE key_digest = ?",
            (*row, _digest(key)),
        )
    assert store.verify_log()["valid"] is True
    _assert_retry_refused(store, 0, IdempotencyConflict)
    _assert_retry_refused(store, 1, IdempotencyConflict)


@pytest.mark.parametrize("missing", [99, -1])
def test_m1_03_receipt_pointing_to_a_nonexistent_event(
    keyed_log: tuple[VerificationLog, str], missing: int
) -> None:
    store, path = keyed_log
    _sql(
        path, "UPDATE vlog_idempotency SET idx = ? WHERE key_digest = ?", (missing, _digest("k-2"))
    )
    assert _has(_problems(store), f"names missing event {missing}")
    _assert_retry_refused(store, 2, LogCorruption)


def test_m1_03b_receipt_whose_own_index_names_a_nonexistent_event(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    store, path = keyed_log
    receipt = json.loads(_row(path, "k-2")[2])
    receipt["index"] = 99
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (json.dumps(receipt), _digest("k-2")),
    )
    problems = _problems(store)
    assert _has(problems, "receipt names event 99, row names 2")
    assert _has(problems, "receipt does not verify")
    _assert_retry_refused(store, 2, LogCorruption)


@pytest.mark.parametrize("receipt", ["", "not json", "[]", "null", "{}"])
def test_m1_04_idempotency_row_without_a_receipt(
    keyed_log: tuple[VerificationLog, str], receipt: str
) -> None:
    """The column is NOT NULL; an empty, unparsable or empty-object receipt is reported."""
    store, path = keyed_log
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (receipt, _digest("k-1")),
    )
    problems = _problems(store)
    assert any(problem.startswith("idempotency key ") for problem in problems)
    _assert_retry_refused(store, 1, LogCorruption)


def test_m1_04b_receipt_column_cannot_be_null(keyed_log: tuple[VerificationLog, str]) -> None:
    _, path = keyed_log
    with pytest.raises(sqlite3.IntegrityError):
        _sql(
            path,
            "UPDATE vlog_idempotency SET receipt = NULL WHERE key_digest = ?",
            (_digest("k-1"),),
        )


def test_m1_05_receipt_without_an_idempotency_row(tmp_path: Path) -> None:
    """Not applicable by design: keys are optional and the tree does not record them.

    An event sent without a key has a receipt and no row, and the log is valid. If a
    row is deleted, a retry appends the event again; that is visible as a second
    event with the same input, and only the client's receipt can prove which came
    first. ``verify_log()`` cannot detect a missing row (documented limitation).
    """
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        unkeyed = store.append(_event(0))
        keyed = store.append(_event(1), idempotency_key="k-1")
        assert verify_receipt(unkeyed, store.verifier_key)
        assert store.verify_log()["valid"] is True
        _sql(path, "DELETE FROM vlog_idempotency WHERE key_digest = ?", (_digest("k-1"),))
        assert store.verify_log()["valid"] is True
        again = store.append(_event(1), idempotency_key="k-1")
        assert again["index"] == 2 != keyed["index"]
        assert again["record"]["input_sha256"] == keyed["record"]["input_sha256"]


def test_m1_06_request_input_altered(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    _sql(
        path,
        "UPDATE vlog_idempotency SET input_sha256 = ? WHERE key_digest = ?",
        ("f" * 64, _digest("k-3")),
    )
    assert _has(_problems(store), "receipt record input differs from the request input")
    # The original request no longer matches the row: refused, nothing appended.
    _assert_retry_refused(store, 3, IdempotencyConflict)


def test_m1_06b_request_input_made_malformed(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    _sql(
        path,
        "UPDATE vlog_idempotency SET input_sha256 = 'x' WHERE key_digest = ?",
        (_digest("k-3"),),
    )
    assert _has(_problems(store), "receipt record input differs")


@pytest.mark.parametrize("new_idx", [0, 1, 3])
def test_m1_07_event_index_altered(keyed_log: tuple[VerificationLog, str], new_idx: int) -> None:
    store, path = keyed_log
    _sql(
        path, "UPDATE vlog_idempotency SET idx = ? WHERE key_digest = ?", (new_idx, _digest("k-2"))
    )
    problems = _problems(store)
    assert _has(problems, f"receipt names event 2, row names {new_idx}")
    assert _has(problems, f"receipt leaf differs from stored leaf {new_idx}")
    assert _has(problems, f"event {new_idx} is named by more than one key")
    _assert_retry_refused(store, 2, LogCorruption)


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda r: r["record"].update(verdict="SUPPORTED"), id="verdict"),
        pytest.param(lambda r: r["record"].update(client="someone-else"), id="client"),
        pytest.param(lambda r: r.update(salt=base64.b64encode(bytes(32)).decode()), id="salt"),
        pytest.param(lambda r: r["record"].update(input_sha256="e" * 64), id="input"),
    ],
)
def test_m1_08_divergent_commitment(keyed_log: tuple[VerificationLog, str], mutate: Any) -> None:
    """Receipt record or salt no longer opens the leaf commitment."""
    store, path = keyed_log
    receipt = json.loads(_row(path, "k-0")[2])
    mutate(receipt)
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (json.dumps(receipt), _digest("k-0")),
    )
    assert _has(_problems(store), "receipt does not verify (signature, inclusion or commitment)")
    _assert_retry_refused(store, 0, LogCorruption)


def test_m1_09_duplicate_event_index_across_keys(keyed_log: tuple[VerificationLog, str]) -> None:
    """A second key naming an event already named by another key."""
    store, path = keyed_log
    input_sha256, idx, receipt = _row(path, "k-1")
    _sql(
        path,
        _INSERT,
        (_digest("k-1-copy"), input_sha256, idx, receipt),
    )
    assert _has(_problems(store), "event 1 is named by more than one key")


def test_m1_09b_malformed_key_digest_is_reported(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    _sql(
        path,
        "UPDATE vlog_idempotency SET key_digest = 'XYZ' WHERE key_digest = ?",
        (_digest("k-1"),),
    )
    assert _has(_problems(store), "malformed key digest")


def test_m1_09c_duplicate_key_digest_is_refused_by_the_schema(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    _, path = keyed_log
    with pytest.raises(sqlite3.IntegrityError):
        _sql(
            path,
            _INSERT,
            (_digest("k-1"), "0" * 64, 0, "{}"),
        )


def test_m1_10_retry_after_tamper_never_returns_or_appends(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    """After any receipt tamper, the retry raises before returning and the tree is unchanged."""
    store, path = keyed_log
    size = store.size()
    _, _, original = _row(path, "k-1")
    _, _, receipt_3 = _row(path, "k-3")
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (receipt_3, _digest("k-1")),
    )
    for _ in range(3):
        _assert_retry_refused(store, 1, LogCorruption)
    assert store.size() == size
    # Restoring the original receipt restores retries and the log is valid again.
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (original, _digest("k-1")),
    )
    assert store.verify_log()["valid"] is True
    assert store.append(_event(1, verdict=_verdict(1)), idempotency_key="k-1") == json.loads(
        original
    )


def test_m1_11_reopen_and_offline_verification(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        first = store.append(_event(0, verdict="REFUTED"), idempotency_key="k-0")
        store.append(_event(1), idempotency_key="k-1")
        vkey = store.verifier_key
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as reopened:
        assert reopened.verify_log()["valid"] is True
        again = reopened.append(_event(0, verdict="REFUTED"), idempotency_key="k-0")
        assert again == first
        assert reopened.size() == 2
    # Offline: only the receipt and the public verifier key.
    assert verify_receipt(json.loads(json.dumps(again)), vkey) is True
    # Tamper while closed, then reopen: reported, and the retry is refused.
    _, _, receipt_1 = _row(path, "k-1")
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (receipt_1, _digest("k-0")),
    )
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as reopened:
        assert _has(_problems(reopened), "receipt names event 1, row names 0")
        with pytest.raises(LogCorruption):
            reopened.append(_event(0, verdict="REFUTED"), idempotency_key="k-0")
        assert reopened.size() == 2


def test_m1_12_direct_db_tamper_with_a_receipt_signed_by_another_key(
    keyed_log: tuple[VerificationLog, str], tmp_path: Path
) -> None:
    """An attacker without the log key re-signs a forged receipt with their own key."""
    store, path = keyed_log
    forged_path = str(tmp_path / "forged.sqlite3")
    with VerificationLog(forged_path, NoteSigner(ORIGIN, bytes(32))) as forger:
        for n in range(4):
            forged = forger.append(_event(n, verdict="SUPPORTED"))
    assert forged["index"] == 3
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (json.dumps(forged), _digest("k-3")),
    )
    problems = _problems(store)
    assert _has(problems, "receipt leaf differs from stored leaf 3")
    assert _has(problems, "receipt does not verify")
    _assert_retry_refused(store, 3, LogCorruption)


def test_m1_12b_tamper_leaves_other_keys_working(keyed_log: tuple[VerificationLog, str]) -> None:
    """Only the tampered key is refused; problems name only that key."""
    store, path = keyed_log
    _sql(path, "UPDATE vlog_idempotency SET receipt = '{}' WHERE key_digest = ?", (_digest("k-0"),))
    problems = _problems(store)
    assert all(problem.startswith(f"idempotency key {_digest('k-0')[:12]}") for problem in problems)
    assert store.append(_event(1, verdict=_verdict(1)), idempotency_key="k-1")["index"] == 1


# --- M2: LGPD erasure also redacts the idempotency receipt -----------------------


def test_m2_erasure_redacts_the_stored_receipt(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    original = json.loads(_row(path, "k-0")[2])
    erasure = store.erase(0, "2026-11-22T00:00:00Z")
    _, idx, receipt_text = _row(path, "k-0")
    assert idx == 0
    assert json.loads(receipt_text) == {"redacted": True, "index": 0, "erasure_index": erasure}
    # No record or salt remains anywhere in the row.
    assert original["salt"] not in receipt_text
    assert "client-a" not in receipt_text and "REFUTED" not in receipt_text
    assert store.verify_log()["valid"] is True


def test_m2_retry_of_an_erased_event_is_refused(keyed_log: tuple[VerificationLog, str]) -> None:
    store, _ = keyed_log
    store.erase(0, "2026-11-22T00:00:00Z")
    size = store.size()
    with pytest.raises(IdempotencyErased):
        store.append(_event(0, verdict="REFUTED"), idempotency_key="k-0")
    # IdempotencyErased is an IdempotencyConflict, so the API answers 409.
    assert issubclass(IdempotencyErased, IdempotencyConflict)
    assert store.size() == size
    # A different input under the same key is still a plain conflict.
    with pytest.raises(IdempotencyConflict):
        store.append(_event(9), idempotency_key="k-0")


def test_m2_restoring_the_full_receipt_after_erasure_is_reported(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    """Also the state of a database erased before this fix (migration note)."""
    store, path = keyed_log
    original = _row(path, "k-0")[2]
    store.erase(0, "2026-11-22T00:00:00Z")
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (original, _digest("k-0")),
    )
    assert _has(_problems(store), "receipt keeps the record and salt of erased event 0")
    _assert_retry_refused(store, 0, LogCorruption)


@pytest.mark.parametrize(
    "redacted",
    [
        pytest.param({"redacted": True, "index": 1, "erasure_index": 4}, id="event-not-erased"),
        pytest.param({"redacted": True, "index": 0}, id="missing-field"),
        pytest.param({"redacted": True, "index": 0, "erasure_index": 4, "x": 1}, id="extra-field"),
        pytest.param({"redacted": True, "index": 0, "erasure_index": 2}, id="points-to-an-event"),
        pytest.param({"redacted": True, "index": 0, "erasure_index": 77}, id="points-nowhere"),
        pytest.param({"redacted": True, "index": 0, "erasure_index": "4"}, id="index-type"),
    ],
)
def test_m2_forged_redacted_receipts_are_reported(
    keyed_log: tuple[VerificationLog, str], redacted: dict[str, Any]
) -> None:
    store, path = keyed_log
    assert store.erase(0, "2026-11-22T00:00:00Z") == 4
    key = f"k-{redacted['index']}" if redacted["index"] == 1 else "k-0"
    _sql(
        path,
        "UPDATE vlog_idempotency SET receipt = ? WHERE key_digest = ?",
        (json.dumps(redacted), _digest(key)),
    )
    problems = _problems(store)
    assert any(problem.startswith(f"idempotency key {_digest(key)[:12]}") for problem in problems)


def test_m2_redaction_survives_reopen(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0), idempotency_key="k-0")
        store.erase(0, "2026-11-22T00:00:00Z")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as reopened:
        assert reopened.verify_log()["valid"] is True
        with pytest.raises(IdempotencyErased):
            reopened.append(_event(0), idempotency_key="k-0")


# --- malformed rows and leaves ----------------------------------------------------------


def test_row_naming_an_erasure_leaf_is_reported(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    erasure_index = store.erase(1, "2026-11-22T00:00:00Z")
    _sql(
        path,
        "UPDATE vlog_idempotency SET idx = ? WHERE key_digest = ?",
        (erasure_index, _digest("k-2")),
    )
    assert _has(_problems(store), f"leaf {erasure_index} is not an event")
    _assert_retry_refused(store, 2, LogCorruption)


def test_row_with_a_non_integer_index_is_reported(keyed_log: tuple[VerificationLog, str]) -> None:
    store, path = keyed_log
    _sql(path, "UPDATE vlog_idempotency SET idx = 'two' WHERE key_digest = ?", (_digest("k-2"),))
    assert _has(_problems(store), "malformed row")
    _assert_retry_refused(store, 2, LogCorruption)


def test_row_naming_a_leaf_that_is_not_json_is_reported(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    store, path = keyed_log
    _sql(path, "UPDATE vlog_leaves SET leaf = X'ff00' WHERE idx = 2")
    problems = _problems(store)
    assert _has(problems, "leaf 2 is not an event")
    assert "leaf 2 hash mismatch" in problems


def test_redacted_receipt_pointing_to_a_leaf_that_is_not_json_is_reported(
    keyed_log: tuple[VerificationLog, str],
) -> None:
    store, path = keyed_log
    erasure_index = store.erase(0, "2026-11-22T00:00:00Z")
    _sql(path, "UPDATE vlog_leaves SET leaf = X'ff00' WHERE idx = ?", (erasure_index,))
    assert _has(_problems(store), "redacted receipt does not point to the erasure of event 0")
