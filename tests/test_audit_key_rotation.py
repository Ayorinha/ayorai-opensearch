"""HMAC key rotation: old traces are resealed with the new key, never laundered."""

from __future__ import annotations

import sqlite3
from contextlib import closing
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


def _key_ids(path: str) -> list[str]:
    with closing(sqlite3.connect(path)) as connection:
        return [row[0] for row in connection.execute("SELECT mac_key_id FROM audit_traces")]


def test_rotation_reseals_valid_traces_so_the_old_key_can_be_retired(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        traces = [_record(store) for _ in range(3)]
    with AuditTraceStore(path, mac_keys=(NEW, OLD)) as store:
        fresh = _record(store)
        assert store.reseal_with_active_key() == {"resealed": 3, "skipped_invalid": 0}
        assert store.reseal_with_active_key() == {"resealed": 0, "skipped_invalid": 0}
    assert set(_key_ids(path)) == {"k2"}
    with AuditTraceStore(path, mac_keys=(NEW,)) as store:  # old key retired
        assert store.verify_all() == {"valid": 4, "invalid": 0}
        assert all(store.verify(trace) == "valid" for trace in [*traces, fresh])


def test_an_altered_trace_is_not_laundered_by_rotation(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=(OLD,)) as store:
        good, bad = _record(store), _record(store)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE audit_traces SET owner = 'mallory' WHERE trace_id = ?", (bad,))
    with AuditTraceStore(path, mac_keys=(NEW, OLD)) as store:
        assert store.reseal_with_active_key() == {"resealed": 1, "skipped_invalid": 1}
        assert store.verify(good) == "valid"
        assert store.verify(bad) == "invalid"
    with AuditTraceStore(path, mac_keys=(NEW,)) as store:
        assert store.verify(bad) == "invalid"


def test_rotation_requires_keys(tmp_path: Path) -> None:
    with AuditTraceStore(str(tmp_path / "a.sqlite3"), mac_keys=()) as store:
        with pytest.raises(ValueError, match="ATTRACTOR_AUDIT_HMAC_KEYS"):
            store.reseal_with_active_key()


def test_unsealed_traces_are_left_to_seal_unsealed(tmp_path: Path) -> None:
    path = str(tmp_path / "a.sqlite3")
    with AuditTraceStore(path, mac_keys=()) as store:
        _record(store)
    with AuditTraceStore(path, mac_keys=(NEW,)) as store:
        assert store.reseal_with_active_key() == {"resealed": 0, "skipped_invalid": 0}
        assert store.seal_unsealed() == 1
        assert store.verify_all() == {"valid": 1, "invalid": 0}
