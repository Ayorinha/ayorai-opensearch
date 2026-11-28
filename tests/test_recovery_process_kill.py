"""P4: a process killed mid-write (SIGKILL, no cleanup) leaves each durable store usable.

``test_audit_store_durability.py`` covers the audit trail. These tests cover the
other two SQLite stores: the signed verification log (ADR-010) and the job queue.
Each round kills a writer at an arbitrary point, possibly inside a transaction, then
reopens the database and checks that nothing is torn and that work can continue.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationLog, verify_receipt
from ayorai_attractor.job_store import JobStatus, JobStore
from tests.test_verify_log import ORIGIN, SEED, _event

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="SIGKILL of a forked writer is exercised on Linux"
)


def _integrity(path: Path) -> str:
    with closing(sqlite3.connect(str(path))) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def _rows(path: Path, table: str) -> int:
    with closing(sqlite3.connect(str(path), timeout=5)) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # noqa: S608


def _kill_rounds(target: object, path: Path, table: str, rounds: int = 3) -> None:
    # "spawn", not "fork": the test process may already run threads, and forking a
    # multi-threaded process can deadlock the child.
    context = multiprocessing.get_context("spawn")
    for round_ in range(rounds):
        before = _rows(path, table)
        child = context.Process(target=target, args=(str(path), round_))
        child.start()
        deadline = time.monotonic() + 30
        while _rows(path, table) < before + 20:  # kill only once the child is writing
            assert time.monotonic() < deadline, "writer never started"
            time.sleep(0.05)
        assert child.pid is not None
        os.kill(child.pid, signal.SIGKILL)  # no cleanup, possibly inside a transaction
        child.join(10)
        assert child.exitcode == -signal.SIGKILL


# --- verification log ----------------------------------------------------------------


def _append_forever(path: str, round_: int) -> None:
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as log:
        n = round_ * 1_000_000
        while True:
            log.append(_event(n), idempotency_key=f"k-{n}")
            n += 1


def test_a_verification_log_killed_while_appending_stays_valid(tmp_path: Path) -> None:
    path = tmp_path / "verify.sqlite3"
    VerificationLog(str(path), NoteSigner(ORIGIN, SEED)).close()
    _kill_rounds(_append_forever, path, "vlog_leaves")

    assert _integrity(path) == "ok"
    with VerificationLog(str(path), NoteSigner(ORIGIN, SEED)) as log:
        report = log.verify_log()
        assert report["valid"] is True, report["problems"]
        size = log.size()
        assert size > 0
        # The log keeps working: a new event gets a receipt that verifies offline,
        # and a retry with the same key returns the stored receipt.
        receipt = log.append(_event(10**9), idempotency_key="after-recovery")
        assert verify_receipt(receipt, log.verifier_key)
        assert log.append(_event(10**9), idempotency_key="after-recovery") == receipt
        assert log.size() == size + 1
        assert log.verify_log()["valid"] is True


# --- job queue -----------------------------------------------------------------------


def _work_forever(path: str, round_: int) -> None:
    with JobStore(path) as store:
        n = 0
        while True:
            job_id = f"r{round_}-j{n}"
            store.enqueue(job_id, f"key-{job_id}")
            job = store.claim(job_id, lease_seconds=60.0, now=1000.0)
            if n % 2:
                store.finish(job_id, success=True, attempt=job.attempts)
            n += 1


def test_a_job_store_killed_while_working_recovers_every_job(tmp_path: Path) -> None:
    path = tmp_path / "jobs.sqlite3"
    JobStore(str(path)).close()
    _kill_rounds(_work_forever, path, "jobs")

    assert _integrity(path) == "ok"
    with closing(sqlite3.connect(str(path))) as connection:
        job_ids = [str(row[0]) for row in connection.execute("SELECT job_id FROM jobs")]
    assert job_ids
    with JobStore(str(path)) as store:
        # Leases taken by the killed workers expire and the jobs return to the queue.
        store.reclaim_expired(now=10_000.0)
        statuses = {store.get(job_id).status for job_id in job_ids}
        assert statuses <= {JobStatus.QUEUED, JobStatus.SUCCEEDED}
        assert JobStatus.RUNNING not in statuses
        # A requeued job can be claimed and finished by a new worker.
        queued = [j for j in job_ids if store.get(j).status is JobStatus.QUEUED]
        if queued:
            job = store.claim(queued[0], lease_seconds=60.0, now=10_001.0)
            finished = store.finish(queued[0], success=True, attempt=job.attempts)
            assert finished.status is JobStatus.SUCCEEDED
