import sqlite3
from collections.abc import Iterator

import pytest

from ayorai_attractor.job_store import JobStatus, JobStore


@pytest.fixture
def store() -> Iterator[JobStore]:
    instance = JobStore()
    try:
        yield instance
    finally:
        instance.close()


def test_job_lifecycle_is_restartable_metadata(store: JobStore) -> None:
    queued = store.enqueue("job-1", "request-1")
    assert queued.status is JobStatus.QUEUED
    assert queued.attempts == 0
    running = store.claim("job-1", now=100.0, lease_seconds=30.0)
    assert running.status is JobStatus.RUNNING
    assert running.attempts == 1
    assert running.lease_until == 130.0
    finished = store.finish("job-1", success=True, attempt=running.attempts)
    assert finished.status is JobStatus.SUCCEEDED
    assert finished.lease_until is None


def test_idempotency_key_deduplicates_enqueue(store: JobStore) -> None:
    first = store.enqueue("job-1", "same-request")
    second = store.enqueue("job-2", "same-request")
    assert second == first


def test_invalid_state_transition_is_rejected(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    with pytest.raises(ValueError, match="only running"):
        store.finish("job-1", success=True, attempt=1)
    running = store.claim("job-1", now=100.0)
    store.finish("job-1", success=False, attempt=running.attempts)
    with pytest.raises(ValueError, match="only queued"):
        store.claim("job-1")


def test_expired_lease_is_requeued_and_can_be_claimed_again(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    first = store.claim("job-1", now=100.0, lease_seconds=10.0)
    assert store.reclaim_expired(now=109.0) == 0
    assert store.reclaim_expired(now=110.0) == 1
    second = store.claim("job-1", now=111.0, lease_seconds=10.0)
    assert second.status is JobStatus.RUNNING
    assert second.attempts == 2
    assert first.lease_until == 110.0


def test_lease_must_be_positive(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    with pytest.raises(ValueError, match="lease_seconds"):
        store.claim("job-1", lease_seconds=0)


def test_job_store_context_manager_closes_connection() -> None:
    with JobStore() as managed:
        managed.enqueue("context-job", "context-request")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        managed.get("context-job")


def test_job_store_close_is_idempotent() -> None:
    store = JobStore()
    store.close()
    store.close()


def test_reenqueue_same_job_and_key_returns_stored_job(store: JobStore) -> None:
    first = store.enqueue("job-1", "request-1")
    store.claim("job-1", now=100.0)
    again = store.enqueue("job-1", "request-1")
    assert again.job_id == first.job_id
    assert again.status is JobStatus.RUNNING


def test_job_id_reused_under_another_key_is_rejected(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    with pytest.raises(sqlite3.IntegrityError):
        store.enqueue("job-1", "request-2")


def test_stale_lease_cannot_finish_a_job_claimed_again(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    stale = store.claim("job-1", now=100.0, lease_seconds=10.0)
    assert store.reclaim_expired(now=111.0) == 1
    current = store.claim("job-1", now=111.0, lease_seconds=10.0)

    with pytest.raises(ValueError, match="stale lease"):
        store.finish("job-1", success=False, attempt=stale.attempts)
    assert store.get("job-1").status is JobStatus.RUNNING

    finished = store.finish("job-1", success=True, attempt=current.attempts)
    assert finished.status is JobStatus.SUCCEEDED


def test_finish_with_matching_attempt_on_finished_job_is_rejected(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    claimed = store.claim("job-1", now=100.0)
    store.finish("job-1", success=True, attempt=claimed.attempts)
    with pytest.raises(ValueError, match="only running"):
        store.finish("job-1", success=True, attempt=claimed.attempts)


def test_finish_requires_attempt_fencing(store: JobStore) -> None:
    store.enqueue("job-1", "request-1")
    store.claim("job-1", now=100.0)

    with pytest.raises(TypeError, match="attempt"):
        store.finish("job-1", success=True)  # type: ignore[call-arg]


def test_concurrent_enqueue_on_one_key_yields_one_job(tmp_path: object) -> None:
    import threading
    from pathlib import Path

    path = str(Path(str(tmp_path)) / "jobs.sqlite3")
    JobStore(path).close()
    workers = 8
    stores = [JobStore(path) for _ in range(workers)]
    barrier = threading.Barrier(workers)
    results: list[str] = []
    errors: list[BaseException] = []

    def produce(index: int) -> None:
        barrier.wait()
        try:
            results.append(stores[index].enqueue(f"job-{index}", "same-request").job_id)
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=produce, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for instance in stores:
        instance.close()

    assert errors == []
    assert len(set(results)) == 1
    with JobStore(path) as check:
        count = check._connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert count == 1
