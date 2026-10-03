"""Durable orchestration state primitives for R9.

The store persists control-plane metadata only. Payloads should be references to
already governed artifacts, not raw prompts, secrets, or model outputs.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class Job:
    job_id: str
    idempotency_key: str
    status: JobStatus
    attempts: int
    lease_until: float | None = None


class JobStore:
    """SQLite-backed state machine with restart-safe leases."""

    def __init__(self, path: str = ":memory:") -> None:
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                lease_until REAL
            )
            """
        )
        columns = {
            row[1]
            for row in self._connection.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "lease_until" not in columns:
            self._connection.execute("ALTER TABLE jobs ADD COLUMN lease_until REAL")
        self._connection.commit()

    def enqueue(self, job_id: str, idempotency_key: str) -> Job:
        existing = self._connection.execute(
            "SELECT job_id, idempotency_key, status, attempts, lease_until "
            "FROM jobs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            return self._from_row(existing)
        self._connection.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
            (job_id, idempotency_key, JobStatus.QUEUED.value, 0, None),
        )
        self._connection.commit()
        return self.get(job_id)

    def claim(
        self,
        job_id: str,
        *,
        lease_seconds: float = 300.0,
        now: float | None = None,
    ) -> Job:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        timestamp = time.time() if now is None else now
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._requeue_expired(timestamp)
            updated = self._connection.execute(
                "UPDATE jobs SET status = ?, attempts = attempts + 1, "
                "lease_until = ? WHERE job_id = ? AND status = ?",
                (
                    JobStatus.RUNNING.value,
                    timestamp + lease_seconds,
                    job_id,
                    JobStatus.QUEUED.value,
                ),
            ).rowcount
            if updated != 1:
                self._connection.rollback()
                job = self.get(job_id)
                raise ValueError("only queued jobs can be claimed")
            self._connection.commit()
        except Exception:
            if self._connection.in_transaction:
                self._connection.rollback()
            raise
        return self.get(job_id)

    def finish(self, job_id: str, *, success: bool) -> Job:
        job = self.get(job_id)
        if job.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can be finished")
        status = JobStatus.SUCCEEDED if success else JobStatus.FAILED
        self._connection.execute(
            "UPDATE jobs SET status = ?, lease_until = NULL WHERE job_id = ?",
            (status.value, job_id),
        )
        self._connection.commit()
        return self.get(job_id)

    def reclaim_expired(self, *, now: float | None = None) -> int:
        """Return expired running jobs to the queue and report how many changed."""
        timestamp = time.time() if now is None else now
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            count = self._requeue_expired(timestamp)
            self._connection.commit()
            return count
        except Exception:
            if self._connection.in_transaction:
                self._connection.rollback()
            raise

    def get(self, job_id: str) -> Job:
        row = self._connection.execute(
            "SELECT job_id, idempotency_key, status, attempts, lease_until "
            "FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._from_row(row)

    def _requeue_expired(self, now: float) -> int:
        return self._connection.execute(
            "UPDATE jobs SET status = ?, lease_until = NULL "
            "WHERE status = ? AND lease_until IS NOT NULL AND lease_until <= ?",
            (JobStatus.QUEUED.value, JobStatus.RUNNING.value, now),
        ).rowcount

    @staticmethod
    def _from_row(row: tuple[str, str, str, int, float | None]) -> Job:
        return Job(
            job_id=row[0],
            idempotency_key=row[1],
            status=JobStatus(row[2]),
            attempts=row[3],
            lease_until=row[4],
        )
