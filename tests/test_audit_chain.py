"""Sequence chain of the audit store: deletion, insertion, purge, rotation, rollback."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import QualityMode, SearchRequest
from ayorai_attractor.orchestrator import Attractor

OLD = ("k1", b"\x01" * 32)
NEW = ("k2", b"\x02" * 32)


def _record(store: AuditTraceStore, owner: str = "alice") -> str:
    response = Attractor().run(SearchRequest(query="receita da Vértice", mode=list(QualityMode)[0]))
    report = AuditReport.from_response(response)
    store.record(response, report, owner=owner)
    return report.trace_id


def _sql(path: str, statement: str, params: tuple[object, ...] = ()) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement, params)
        connection.commit()


@pytest.mark.parametrize("keys", [(OLD,), ()], ids=["hmac", "sha256"])
def test_fresh_chain_is_intact_and_complete(tmp_path: Path, keys: tuple) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=keys) as store:
        for _ in range(3):
            _record(store)
        report = store.verify_chain(store.checkpoint())
    assert report["intact"] is True
    assert report["complete"] is True
    assert report["entries"] == 3
    assert report["head"]["seq"] == 3


def test_deleting_a_trace_in_the_middle_is_detected(tmp_path: Path) -> None:
    # P2-1: verify_all() alone stays {valid: n, invalid: 0} after a DELETE.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        traces = [_record(store) for _ in range(3)]
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (traces[1],))
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify_all() == {"valid": 2, "invalid": 0}
        report = store.verify_chain()
    assert report["intact"] is False
    assert report["missing_traces"] == 1


def test_deleting_trace_and_its_chain_entry_breaks_the_chain(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        traces = [_record(store) for _ in range(3)]
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (traces[1],))
    _sql(path, "DELETE FROM audit_chain WHERE trace_id = ?", (traces[1],))
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        report = store.verify_chain()
    assert report["intact"] is False
    assert report["broken_links"] >= 1
    assert report["missing_traces"] == 0


def test_renumbering_the_chain_after_a_deletion_is_detected(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        traces = [_record(store) for _ in range(3)]
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (traces[1],))
    _sql(path, "DELETE FROM audit_chain WHERE trace_id = ?", (traces[1],))
    _sql(path, "UPDATE audit_chain SET seq = 2 WHERE seq = 3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        report = store.verify_chain()
    assert report["intact"] is False
    assert report["broken_links"] >= 1


def test_trace_inserted_without_the_api_is_unsequenced(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        original = _record(store)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            "INSERT INTO audit_traces SELECT 'tr_forged', legacy_verification, verification, "
            "operation_status, evidence_count, independent_evidence_count, "
            "verified_evidence_count, failure_count, finding_count, replay_digest, "
            "replay_version, schema_version, owner, recorded_at, software_version, "
            "replay_mac, mac_key_id, check_trace_id, adjudication_sha256 "
            "FROM audit_traces WHERE trace_id = ?",
            (original,),
        )
        connection.commit()
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        report = store.verify_chain()
    assert report["unsequenced_traces"] == 1
    assert report["complete"] is False


def test_rewriting_a_chained_digest_is_detected(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        trace = _record(store)
    _sql(path, "UPDATE audit_chain SET replay_digest = ? WHERE trace_id = ?", ("0" * 64, trace))
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        report = store.verify_chain()
    assert report["intact"] is False
    assert report["broken_links"] == 1
    assert report["digest_mismatches"] == 1


def test_downgrading_a_keyed_chain_to_unkeyed_links_is_detected(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        _record(store)
    _sql(path, "UPDATE audit_chain SET key_id = NULL")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify_chain()["broken_links"] == 1


def test_truncation_and_rollback_are_detected_against_an_external_checkpoint(
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "a.sqlite3")
    older = str(tmp_path / "older.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        _record(store)
    shutil.copyfile(path, older)
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        last = _record(store)
        checkpoint = store.checkpoint()
    # Rollback: the whole database replaced by an older copy.
    with AuditTraceStore(older, mac_keys=(OLD,)) as store:
        assert store.verify_chain()["intact"] is True  # undetectable locally
        assert store.verify_chain(checkpoint)["checkpoint_mismatch"] is True
    # Truncation: the newest trace and its entry removed.
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (last,))
    _sql(path, "DELETE FROM audit_chain WHERE trace_id = ?", (last,))
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify_chain()["intact"] is True  # undetectable locally
        report = store.verify_chain(checkpoint)
    assert report["checkpoint_mismatch"] is True
    assert report["intact"] is False


def test_retention_purge_is_recorded_and_not_reported_as_deletion(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    with AuditTraceStore(path, clock=lambda: now[0], mac_keys=(OLD,)) as store:
        _record(store)
        _record(store)
        now[0] += timedelta(days=10)
        kept = _record(store)
        assert store.purge_recorded_before(now[0] - timedelta(days=5)) == 2
        report = store.verify_chain(store.checkpoint())
        assert store.get(kept, requester="alice") is not None
    assert report["intact"] is True
    assert report["missing_traces"] == 0
    assert report["entries"] == 4  # three traces and one purge record


def test_a_purge_record_cannot_cover_a_later_deletion(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    with AuditTraceStore(path, clock=lambda: now[0], mac_keys=(OLD,)) as store:
        _record(store)
        now[0] += timedelta(days=10)
        assert store.purge_recorded_before(now[0] - timedelta(days=5)) == 1
        later = _record(store)
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (later,))
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify_chain()["missing_traces"] == 1


def test_key_rotation_relinks_the_chain_so_the_old_key_can_be_retired(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        for _ in range(2):
            _record(store)
    with AuditTraceStore(path, mac_keys=(NEW, OLD)) as store:
        _record(store)
        assert store.reseal_with_active_key() == {"resealed": 2, "skipped_invalid": 0}
    with AuditTraceStore(path, mac_keys=(NEW,)) as store:
        assert store.verify_all() == {"valid": 3, "invalid": 0}
        assert store.verify_chain()["intact"] is True


def test_a_broken_chain_is_not_relinked_by_rotation(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        traces = [_record(store) for _ in range(3)]
    _sql(path, "DELETE FROM audit_traces WHERE trace_id = ?", (traces[1],))
    with AuditTraceStore(path, mac_keys=(NEW, OLD)) as store:
        store.reseal_with_active_key()
        assert store.verify_chain()["missing_traces"] == 1
    with closing(sqlite3.connect(path)) as connection:
        assert {row[0] for row in connection.execute("SELECT key_id FROM audit_chain")} == {"k1"}


def test_store_without_chain_is_sequenced_once(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        for _ in range(2):
            _record(store)
    _sql(path, "DELETE FROM audit_chain")  # as a store created before the chain existed
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        assert store.verify_chain()["unsequenced_traces"] == 2
        assert store.sequence_unsequenced() == 2
        assert store.sequence_unsequenced() == 0
        assert store.verify_chain()["complete"] is True


def test_backup_carries_the_chain(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    copy = str(tmp_path / "backup.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        _record(store)
        checkpoint = store.checkpoint()
        store.backup(copy)
    with AuditTraceStore(copy, mac_keys=(OLD,)) as store:
        assert store.verify_chain(checkpoint)["complete"] is True


def test_failed_chain_append_rolls_back_the_trace(tmp_path: Path) -> None:
    # A trace whose chain entry could not be written must not be committed later
    # by an unrelated successful call: the caller was told the record failed.
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        original = store._append_chain_locked

        def failing(*args: object, **kwargs: object) -> None:
            raise sqlite3.OperationalError("disk I/O error")

        store._append_chain_locked = failing  # type: ignore[method-assign]
        with pytest.raises(sqlite3.OperationalError):
            _record(store)
        store._append_chain_locked = original  # type: ignore[method-assign]
        _record(store)
        report = store.verify_chain()
        assert store.verify_all() == {"valid": 1, "invalid": 0}
    assert report["unsequenced_traces"] == 0
    assert report["complete"] is True


def test_failed_purge_record_keeps_the_traces(tmp_path: Path) -> None:
    # A purge whose chain record cannot be written must not delete anything:
    # otherwise the deletion would later look like tampering, or go unrecorded.
    path = str(tmp_path / "a.sqlite3")
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    with AuditTraceStore(path, clock=lambda: now[0], mac_keys=(OLD,)) as store:
        old = _record(store)
        now[0] += timedelta(days=10)

        def failing(*args: object, **kwargs: object) -> None:
            raise sqlite3.OperationalError("disk I/O error")

        original = store._append_chain_locked
        store._append_chain_locked = failing  # type: ignore[method-assign]
        with pytest.raises(sqlite3.OperationalError):
            store.purge_recorded_before(now[0] - timedelta(days=5))
        store._append_chain_locked = original  # type: ignore[method-assign]
        _record(store)
        assert store.get(old, requester="alice") is not None
        assert store.verify_chain()["complete"] is True
