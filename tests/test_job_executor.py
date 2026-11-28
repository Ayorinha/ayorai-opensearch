from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from ayorai_attractor.job_executor import JobExecutor
from ayorai_attractor.job_store import Job, JobStatus, JobStore


@pytest.fixture
def store() -> Iterator[JobStore]:
    instance = JobStore(":memory:")
    try:
        yield instance
    finally:
        instance.close()


@dataclass
class Handler:
    fail: bool = False

    def execute(self, job: Job) -> None:
        if self.fail:
            raise RuntimeError("worker failure")


def test_executor_claims_runs_and_finishes_successfully(store: JobStore) -> None:
    store.enqueue("j1", "id-1")

    result = JobExecutor(store, Handler()).run("j1", now=100.0)

    assert result.status is JobStatus.SUCCEEDED
    assert result.attempts == 1
    assert result.lease_until is None


def test_executor_marks_handler_failure_as_failed(
    store: JobStore, caplog: pytest.LogCaptureFixture
) -> None:
    store.enqueue("j1", "id-1")

    with caplog.at_level("WARNING", logger="ayorai_attractor.job_executor"):
        result = JobExecutor(store, Handler(fail=True)).run("j1", now=100.0)

    assert result.status is JobStatus.FAILED
    assert result.attempts == 1
    assert result.lease_until is None
    messages = [r.getMessage() for r in caplog.records if r.name == "ayorai_attractor.job_executor"]
    assert messages == ["job j1 attempt 1 failed: RuntimeError"]
    assert "worker failure" not in caplog.text


def test_executor_success_logs_nothing(store: JobStore, caplog: pytest.LogCaptureFixture) -> None:
    store.enqueue("j1", "id-1")

    with caplog.at_level("DEBUG", logger="ayorai_attractor.job_executor"):
        JobExecutor(store, Handler()).run("j1", now=100.0)

    assert not [r for r in caplog.records if r.name == "ayorai_attractor.job_executor"]


def test_executor_rejects_a_non_queued_job(store: JobStore) -> None:
    store.enqueue("j1", "id-1")
    JobExecutor(store, Handler()).run("j1", now=100.0)

    with pytest.raises(ValueError, match="only queued jobs can be claimed"):
        JobExecutor(store, Handler()).run("j1", now=101.0)


def test_executor_whose_lease_expired_cannot_overwrite_the_new_run(store: JobStore) -> None:
    store.enqueue("j1", "id-1")

    @dataclass
    class SlowHandler:
        def execute(self, job: Job) -> None:
            # While this worker is still running, its lease expires and a
            # second worker reclaims and claims the same job.
            store.reclaim_expired(now=200.0)
            store.claim("j1", now=200.0, lease_seconds=10.0)

    with pytest.raises(ValueError, match="stale lease"):
        JobExecutor(store, SlowHandler()).run("j1", now=100.0, lease_seconds=10.0)

    current = store.get("j1")
    assert current.status is JobStatus.RUNNING
    assert current.attempts == 2
