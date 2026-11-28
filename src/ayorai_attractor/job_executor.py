"""Durable worker integration for the R9 JobStore."""

from __future__ import annotations

import logging
from typing import Protocol

from .job_store import Job, JobStore

logger = logging.getLogger(__name__)


class JobHandler(Protocol):
    def execute(self, job: Job) -> None: ...


class JobExecutor:
    """Claim, execute and finish one durable job without owning its payload."""

    def __init__(self, store: JobStore, handler: JobHandler) -> None:
        self.store = store
        self.handler = handler

    def run(
        self,
        job_id: str,
        *,
        lease_seconds: float = 300.0,
        now: float | None = None,
    ) -> Job:
        job = self.store.claim(job_id, lease_seconds=lease_seconds, now=now)
        try:
            self.handler.execute(job)
        except Exception as exc:
            # Only the exception type: the message may carry payload data.
            logger.warning(
                "job %s attempt %d failed: %s", job.job_id, job.attempts, type(exc).__name__
            )
            return self.store.finish(job.job_id, success=False, attempt=job.attempts)
        return self.store.finish(job.job_id, success=True, attempt=job.attempts)

    def reclaim_expired(self, *, now: float | None = None) -> int:
        return self.store.reclaim_expired(now=now)
