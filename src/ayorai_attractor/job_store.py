"""Durable orchestration state primitives for R9.

The store persists control-plane metadata only. Payloads should be references to
already governed artifacts, not raw prompts, secrets, or model outputs.
"""

from __future__ import annotations

import sqlite3
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


class JobStore:
    """SQLite-backed state machine for restart-safe orchestration metadata."""

    def __init__(self, path: str = ":memory:") -> None:
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL
            )
            """
        )
        self._connection.commit()

    def enqueue(self, job_id: str, idempotency_key: str) -> Job:
        existing = self._connection.execute(
            "SELECT job_id, idempotency_key, status, attempts "
            "FROM jobs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            return self._from_row(existing)
        self._connection.execute(
            "INSERT INTO jobs VALUES (?, ?, ?, ?)",
            (job_id, idempotency_key, JobStatus.QUEUED.value, 0),
        )
        self._connection.commit()
        return self.get(job_id)

    def claim(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status is not JobStatus.QUEUED:
            raise ValueError("only queued jobs can be claimed")
        self._connection.execute(
            "UPDATE jobs SET status = ?, attempts = attempts + 1 WHERE job_id = ?",
            (JobStatus.RUNNING.value, job_id),
        )
        self._connection.commit()
        return self.get(job_id)

    def finish(self, job_id: str, *, success: bool) -> Job:
        job = self.get(job_id)
        if job.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can be finished")
        status = JobStatus.SUCCEEDED if success else JobStatus.FAILED
        self._connection.execute(
            "UPDATE jobs SET status = ? WHERE job_id = ?",
            (status.value, job_id),
        )
        self._connection.commit()
        return self.get(job_id)

    def get(self, job_id: str) -> Job:
        row = self._connection.execute(
            "SELECT job_id, idempotency_key, status, attempts "
            "FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._from_row(row)

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> Job:
        return Job(
            job_id=str(row[0]),
            idempotency_key=str(row[1]),
            status=JobStatus(str(row[2])),
            attempts=int(row[3]),
        )
