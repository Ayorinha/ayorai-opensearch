"""Audit trail: forgeries that a correct link or digest alone would not reveal.

A store without HMAC keys chains entries with plain SHA-256, so anyone with
write access can compute a valid link. These entries must still be rejected
for what they say, not only for how they are linked.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.audit_store import AuditTraceStore
from tests.test_audit_chain import OLD, _record

GENESIS = "genesis"


def _unkeyed_link(seq: int, kind: str, payload: str | None, previous: str) -> str:
    """The documented chain link (ayorai.audit.chain.v1), written independently of the
    implementation, as a writer with database access would compute it."""
    canonical = json.dumps(
        {
            "domain": "ayorai.audit.chain.v1",
            "seq": seq,
            "kind": kind,
            "trace_id": None,
            "replay_digest": None,
            "payload": payload,
            "previous": previous,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _append_forged_entry(path: str, kind: str, payload: str | None) -> None:
    """Append an entry with a correct unkeyed SHA-256 link after the current head."""
    with closing(sqlite3.connect(path)) as connection:
        row = connection.execute(
            "SELECT seq, link FROM audit_chain ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        seq, previous = (int(row[0]) + 1, str(row[1])) if row else (1, GENESIS)
        link = _unkeyed_link(seq, kind, payload, previous)
        connection.execute(
            "INSERT INTO audit_chain (seq, kind, trace_id, replay_digest, payload, link, key_id)"
            " VALUES (?, ?, NULL, NULL, ?, ?, NULL)",
            (seq, kind, payload, link),
        )
        connection.commit()


def test_control_forged_entry_of_a_known_shape_is_accepted_by_the_link_check(
    tmp_path: Path,
) -> None:
    # Control: a well-formed purge of nothing passes, so the next two tests fail
    # only because of what the entry says.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        _record(store)
    _append_forged_entry(path, "purge", '{"seqs": []}')
    with AuditTraceStore(path) as store:
        assert store.verify_chain()["intact"] is True


def test_an_entry_of_unknown_kind_breaks_the_chain(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        _record(store)
    _append_forged_entry(path, "rename", None)
    with AuditTraceStore(path) as store:
        report = store.verify_chain()
    assert report["intact"] is False and report["broken_links"] == 1


@pytest.mark.parametrize(
    "payload",
    ["not json", "{}", '{"seqs": 5}', '{"seqs": [["a", 1]]}', '{"seqs": [[1]]}'],
)
def test_a_malformed_purge_breaks_the_chain(tmp_path: Path, payload: str) -> None:
    # A purge that cannot be read must not silently excuse deleted traces.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        _record(store)
    _append_forged_entry(path, "purge", payload)
    with AuditTraceStore(path) as store:
        report = store.verify_chain()
    assert report["intact"] is False and report["broken_links"] >= 1


def test_a_purge_cannot_excuse_entries_recorded_after_it(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        _record(store)
    _append_forged_entry(path, "purge", '{"seqs": [[1, 99]]}')  # claims future entries too
    with AuditTraceStore(path) as store:
        later = _record(store)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("DELETE FROM audit_traces WHERE trace_id = ?", (later,))
        connection.commit()
    with AuditTraceStore(path) as store:
        report = store.verify_chain()
    assert report["intact"] is False and report["missing_traces"] == 1


@pytest.mark.parametrize("version", ["r9-v1", "", "r2-v0"])
def test_an_unknown_replay_version_is_invalid(tmp_path: Path, version: str) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        trace_id = _record(store)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            "UPDATE audit_traces SET replay_version = ? WHERE trace_id = ?", (version, trace_id)
        )
        connection.commit()
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify(trace_id) == "invalid"


def test_a_downgrade_to_legacy_r2_v1_without_its_verdict_is_invalid(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        trace_id = _record(store)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            "UPDATE audit_traces SET replay_version = 'r2-v1', legacy_verification = NULL "
            "WHERE trace_id = ?",
            (trace_id,),
        )
        connection.commit()
    with AuditTraceStore(path) as store:
        assert store.verify(trace_id) == "invalid"


def test_a_sealed_store_refuses_to_open_without_its_keys(tmp_path: Path) -> None:
    # Fail closed: no silent downgrade of sealed traces to digest-only checks.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        _record(store)
    with pytest.raises(ValueError, match="HMAC"):
        AuditTraceStore(path)


@pytest.mark.parametrize("keys", [((b"k", b"\x01" * 32),), (("k",),), ["not", "pairs"]])
def test_hmac_keys_must_be_pairs_of_id_and_bytes(tmp_path: Path, keys: object) -> None:
    with pytest.raises(ValueError, match="HMAC keys"):
        AuditTraceStore(str(tmp_path / "a.sqlite3"), mac_keys=keys)  # type: ignore[arg-type]


def test_mac_metadata_added_behind_an_unkeyed_store_is_invalid(tmp_path: Path) -> None:
    # Defense in depth: a keyed-looking row seen by a store without keys is never
    # accepted as digest-only.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        trace_id = _record(store)
        assert store.verify(trace_id) == "valid"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute(
                "UPDATE audit_traces SET mac_key_id = 'k1', replay_mac = ? WHERE trace_id = ?",
                ("0" * 64, trace_id),
            )
            connection.commit()
        assert store.verify(trace_id) == "invalid"


def test_a_checkpoint_of_the_empty_store_is_checked_too(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path) as store:
        empty = store.checkpoint()
        assert empty == {"seq": 0, "link": GENESIS}
        _record(store)
        assert store.verify_chain(empty)["checkpoint_mismatch"] is False
        forged = {"seq": 0, "link": "0" * 64}
        report = store.verify_chain(forged)
    assert report["checkpoint_mismatch"] is True and report["intact"] is False
