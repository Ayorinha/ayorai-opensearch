"""Audit traces record when (UTC) and with which software version; retention purge."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from ayorai_attractor import __version__
from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore, _utc_timestamp
from ayorai_attractor.models import SearchResponse


class _Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _record(store: AuditTraceStore, trace_id: str) -> None:
    response = SearchResponse.model_validate(
        {"query": "q", "mode": "balanced", "answer": "a", "trace_id": trace_id}
    )
    store.record(response, AuditReport.from_response(response))


def _row(path: Path, trace_id: str) -> tuple[str | None, str | None]:
    with closing(sqlite3.connect(path)) as connection:
        recorded_at, version = connection.execute(
            "SELECT recorded_at, software_version FROM audit_traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
    return recorded_at, version


def test_recorded_at_and_software_version_are_stored(tmp_path: Path) -> None:
    clock = _Clock(datetime(2026, 11, 15, 9, 30, 1, 250000, tzinfo=UTC))
    with AuditTraceStore(str(tmp_path / "a.sqlite3"), clock=clock) as store:
        _record(store, "tr_1")
        assert store.verify("tr_1") == "valid"
    assert _row(tmp_path / "a.sqlite3", "tr_1") == ("2026-11-15T09:30:01.250000Z", __version__)


def test_timestamps_are_normalized_to_utc_and_sort_as_time() -> None:
    brasilia = timezone(timedelta(hours=-3))
    assert _utc_timestamp(datetime(2026, 11, 15, 6, 0, tzinfo=brasilia)) == (
        "2026-11-15T09:00:00.000000Z"
    )
    moments = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(microseconds=7**k) for k in range(12)]
    stamps = [_utc_timestamp(moment) for moment in moments]
    assert sorted(stamps) == [_utc_timestamp(moment) for moment in sorted(moments)]
    assert len({len(stamp) for stamp in stamps}) == 1  # fixed width


def test_naive_timestamps_are_refused(tmp_path: Path) -> None:
    with AuditTraceStore(str(tmp_path / "a.sqlite3"), clock=lambda: datetime(2026, 1, 1)) as store:
        with pytest.raises(ValueError, match="timezone-aware"):
            _record(store, "tr_naive")
        with pytest.raises(ValueError, match="timezone-aware"):
            store.purge_recorded_before(datetime(2026, 1, 1))


def test_retention_purges_only_traces_older_than_the_cutoff(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    clock = _Clock(datetime(2026, 1, 1, tzinfo=UTC))
    with AuditTraceStore(str(path), clock=clock) as store:
        for day in range(10):
            clock.now = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)
            _record(store, f"tr_day{day}")
        with closing(sqlite3.connect(path)) as connection, connection:  # a legacy trace
            connection.execute(
                "UPDATE audit_traces SET recorded_at = NULL WHERE trace_id = 'tr_day0'"
            )
        removed = store.purge_recorded_before(datetime(2026, 1, 5, tzinfo=UTC))
        assert removed == 3  # days 1, 2, 3 (day 0 has no timestamp, day 4 is the cutoff)
        remaining = {
            trace_id
            for trace_id in (f"tr_day{day}" for day in range(10))
            if store.get(trace_id) is not None
        }
        assert remaining == {
            "tr_day0",
            "tr_day4",
            "tr_day5",
            "tr_day6",
            "tr_day7",
            "tr_day8",
            "tr_day9",
        }
        assert store.purge_recorded_before(datetime(2026, 1, 5, tzinfo=UTC)) == 0


def test_existing_databases_gain_the_new_columns(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path)) as store:
        _record(store, "tr_new")
    with closing(sqlite3.connect(path)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_traces)")}
    assert {"owner", "recorded_at", "software_version"} <= columns
