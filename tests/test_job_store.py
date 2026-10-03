import pytest

from ayorai_attractor.job_store import JobStatus, JobStore


def test_job_lifecycle_is_restartable_metadata() -> None:
    store = JobStore()
    queued = store.enqueue("job-1", "request-1")
    assert queued.status is JobStatus.QUEUED
    assert queued.attempts == 0
    running = store.claim("job-1")
    assert running.status is JobStatus.RUNNING
    assert running.attempts == 1
    finished = store.finish("job-1", success=True)
    assert finished.status is JobStatus.SUCCEEDED


def test_idempotency_key_deduplicates_enqueue() -> None:
    store = JobStore()
    first = store.enqueue("job-1", "same-request")
    second = store.enqueue("job-2", "same-request")
    assert second == first


def test_invalid_state_transition_is_rejected() -> None:
    store = JobStore()
    store.enqueue("job-1", "request-1")
    with pytest.raises(ValueError, match="only running"):
        store.finish("job-1", success=True)
    store.claim("job-1")
    store.finish("job-1", success=False)
    with pytest.raises(ValueError, match="only queued"):
        store.claim("job-1")
