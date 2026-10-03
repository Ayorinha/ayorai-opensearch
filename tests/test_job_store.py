import pytest

from ayorai_attractor.job_store import JobStatus, JobStore


def test_job_lifecycle_is_restartable_metadata() -> None:
    store = JobStore()
    queued = store.enqueue("job-1", "request-1")
    assert queued.status is JobStatus.QUEUED
    assert queued.attempts == 0
    running = store.claim("job-1", now=100.0, lease_seconds=30.0)
    assert running.status is JobStatus.RUNNING
    assert running.attempts == 1
    assert running.lease_until == 130.0
    finished = store.finish("job-1", success=True)
    assert finished.status is JobStatus.SUCCEEDED
    assert finished.lease_until is None


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
    store.claim("job-1", now=100.0)
    store.finish("job-1", success=False)
    with pytest.raises(ValueError, match="only queued"):
        store.claim("job-1")


def test_expired_lease_is_requeued_and_can_be_claimed_again() -> None:
    store = JobStore()
    store.enqueue("job-1", "request-1")
    first = store.claim("job-1", now=100.0, lease_seconds=10.0)
    assert store.reclaim_expired(now=109.0) == 0
    assert store.reclaim_expired(now=110.0) == 1
    second = store.claim("job-1", now=111.0, lease_seconds=10.0)
    assert second.status is JobStatus.RUNNING
    assert second.attempts == 2
    assert first.lease_until == 110.0


def test_lease_must_be_positive() -> None:
    store = JobStore()
    store.enqueue("job-1", "request-1")
    with pytest.raises(ValueError, match="lease_seconds"):
        store.claim("job-1", lease_seconds=0)
