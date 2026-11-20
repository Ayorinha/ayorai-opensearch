"""Audit store backup, restore, crash recovery and multi-process writes (real SQLite files)."""

from __future__ import annotations

import multiprocessing
import os
import shutil
import signal
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import SearchResponse


def _record(
    store: AuditTraceStore, trace_id: str, owner: str | None = "key:0123456789abcdef"
) -> None:
    response = SearchResponse.model_validate(
        {"query": "q", "mode": "balanced", "answer": "a", "trace_id": trace_id}
    )
    store.record(response, AuditReport.from_response(response), owner=owner)


def _integrity(path: Path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def test_backup_and_restore_preserve_every_trace(tmp_path: Path) -> None:
    source = tmp_path / "audit.sqlite3"
    with AuditTraceStore(str(source)) as store:
        for index in range(25):
            _record(store, f"tr_{index:03d}")
        assert store.backup(str(tmp_path / "backup" / "audit.bak")) == 25
    restored = tmp_path / "restored.sqlite3"
    shutil.copyfile(tmp_path / "backup" / "audit.bak", restored)  # restore = copy while stopped
    with AuditTraceStore(str(restored)) as store:
        assert store.verify_all() == {"valid": 25, "invalid": 0}
        saved = store.get("tr_007", requester="key:0123456789abcdef")
        assert saved is not None and saved.replay_integrity == "valid"
        assert store.get("tr_007", requester="key:ffffffffffffffff") is None  # owner survives


def test_backup_is_consistent_while_the_store_keeps_writing(tmp_path: Path) -> None:
    with AuditTraceStore(str(tmp_path / "audit.sqlite3")) as store:
        for index in range(50):
            _record(store, f"tr_pre_{index:03d}")
        stop = threading.Event()

        def writer() -> None:
            index = 0
            while not stop.is_set():
                _record(store, f"tr_live_{index:05d}")
                index += 1

        thread = threading.Thread(target=writer)
        thread.start()
        try:
            counts = [store.backup(str(tmp_path / f"b{n}.sqlite3")) for n in range(5)]
        finally:
            stop.set()
            thread.join(10)
    assert counts == sorted(counts) and counts[0] >= 50
    for n in range(5):
        assert _integrity(tmp_path / f"b{n}.sqlite3") == "ok"
        with AuditTraceStore(str(tmp_path / f"b{n}.sqlite3")) as copy:
            assert copy.verify_all() == {"valid": counts[n], "invalid": 0}


def test_backup_refuses_to_overwrite(tmp_path: Path) -> None:
    existing = tmp_path / "existing.sqlite3"
    existing.write_bytes(b"keep")
    with AuditTraceStore(str(tmp_path / "audit.sqlite3")) as store:
        with pytest.raises(FileExistsError):
            store.backup(str(existing))
    assert existing.read_bytes() == b"keep"


def _write_forever(path: str, prefix: str) -> None:
    store = AuditTraceStore(path)
    index = 0
    while True:
        _record(store, f"{prefix}_{index:06d}")
        index += 1


def test_a_process_killed_while_writing_leaves_a_valid_store(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite3"
    AuditTraceStore(str(path)).close()
    context = multiprocessing.get_context("fork")
    for round_ in range(3):
        child = context.Process(target=_write_forever, args=(str(path), f"tr_r{round_}"))
        child.start()
        time.sleep(0.3)
        assert child.pid is not None
        os.kill(child.pid, signal.SIGKILL)  # no cleanup, possibly inside a transaction
        child.join(10)
        assert child.exitcode == -signal.SIGKILL
    assert _integrity(path) == "ok"
    with AuditTraceStore(str(path)) as store:
        counts = store.verify_all()
    assert counts["invalid"] == 0 and counts["valid"] > 0


def _write_n(path: str, prefix: str, n: int) -> None:
    with AuditTraceStore(path) as store:
        for index in range(n):
            _record(store, f"{prefix}_{index:04d}")


def test_concurrent_writer_processes_lose_nothing(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite3"
    AuditTraceStore(str(path)).close()
    context = multiprocessing.get_context("fork")
    workers = [context.Process(target=_write_n, args=(str(path), f"tr_w{w}", 40)) for w in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(60)
        assert worker.exitcode == 0
    with AuditTraceStore(str(path)) as store:
        assert store.verify_all() == {"valid": 160, "invalid": 0}
    assert _integrity(path) == "ok"
