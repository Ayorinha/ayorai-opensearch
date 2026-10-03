from dataclasses import dataclass

import pytest

from ayorai_attractor.job_executor import JobExecutor
from ayorai_attractor.job_store import Job, JobStatus, JobStore


@dataclass
class Handler:
    fail: bool = False

    def execute(self, job: Job) -> None:
        if self.fail:
            raise RuntimeError("worker failure")


def test_executor_claims_runs_and_finishes_successfully() -> None:
    store = JobStore(":memory:")
    store.enqueue("j1", "id-1")

    result = JobExecutor(store, Handler()).run("j1", now=100.0)

    assert result.status is JobStatus.SUCCEEDED
    assert result.attempts == 1
    assert result.lease_until is None


def test_executor_marks_handler_failure_as_failed() -> None:
    store = JobStore(":memory:")
    store.enqueue("j1", "id-1")

    result = JobExecutor(store, Handler(fail=True)).run("j1", now=100.0)

    assert result.status is JobStatus.FAILED
    assert result.attempts == 1
    assert result.lease_until is None


def test_executor_rejects_a_non_queued_job() -> None:
    store = JobStore(":memory:")
    store.enqueue("j1", "id-1")
    JobExecutor(store, Handler()).run("j1", now=100.0)

    with pytest.raises(ValueError, match="only queued jobs can be claimed"):
        JobExecutor(store, Handler()).run("j1", now=101.0)
