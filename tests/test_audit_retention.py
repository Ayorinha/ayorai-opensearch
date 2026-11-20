"""Automatic retention of audit traces (ATTRACTOR_AUDIT_RETENTION_DAYS)."""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore, audit_retention_days_from_env
from ayorai_attractor.models import SearchResponse

START = datetime(2026, 1, 1, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now


def _record(store: AuditTraceStore, trace_id: str) -> None:
    response = SearchResponse.model_validate(
        {"query": "q", "mode": "balanced", "answer": "a", "trace_id": trace_id}
    )
    store.record(response, AuditReport.from_response(response))


def _ids(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as connection:
        return {row[0] for row in connection.execute("SELECT trace_id FROM audit_traces")}


def test_retention_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ATTRACTOR_AUDIT_RETENTION_DAYS", raising=False)
    clock = _Clock()
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), clock=clock, mac_keys=()) as store:
        assert store.retention_days is None
        _record(store, "tr_old")
        clock.now = START + timedelta(days=10_000)
        _record(store, "tr_new")
    assert _ids(path) == {"tr_old", "tr_new"}


@pytest.mark.parametrize("value", ["abc", "0", "-1", "1.5", "36501"])
def test_invalid_retention_is_refused(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", value)
    with pytest.raises(ValueError, match="ATTRACTOR_AUDIT_RETENTION_DAYS"):
        audit_retention_days_from_env()


@pytest.mark.parametrize(("value", "days"), [("", None), ("  ", None), ("30", 30), ("365", 365)])
def test_retention_values(monkeypatch: pytest.MonkeyPatch, value: str, days: int | None) -> None:
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", value)
    assert audit_retention_days_from_env() == days


def test_expired_traces_are_purged_at_startup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "a.sqlite3"
    clock = _Clock()
    with AuditTraceStore(str(path), clock=clock, mac_keys=()) as store:
        for day in (0, 10, 29, 31):
            clock.now = START + timedelta(days=day)
            _record(store, f"tr_day{day}")
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", "30")
    clock.now = START + timedelta(days=40)
    with AuditTraceStore(str(path), clock=clock, mac_keys=()):
        pass
    # Cutoff is day 10: traces recorded before it are gone, day 10 itself stays.
    assert _ids(path) == {"tr_day10", "tr_day29", "tr_day31"}


def test_purge_runs_on_writes_at_most_once_per_hour(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", "1")
    path = tmp_path / "a.sqlite3"
    clock = _Clock()
    with AuditTraceStore(str(path), clock=clock, mac_keys=()) as store:
        _record(store, "tr_a")
        clock.now = START + timedelta(minutes=30)  # the startup run was 30 minutes ago
        _record(store, "tr_b")
        assert _ids(path) == {"tr_a", "tr_b"}
        clock.now = START + timedelta(days=2)
        _record(store, "tr_c")  # more than an hour since the last run: purge happens
        assert _ids(path) == {"tr_c"}
        clock.now = START + timedelta(days=2, minutes=10)
        _record(store, "tr_d")
        assert _ids(path) == {"tr_c", "tr_d"}


def test_traces_without_recorded_at_are_never_purged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "a.sqlite3"
    clock = _Clock()
    with AuditTraceStore(str(path), clock=clock, mac_keys=()) as store:
        _record(store, "tr_legacy")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE audit_traces SET recorded_at = NULL")
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", "1")
    clock.now = START + timedelta(days=400)
    with AuditTraceStore(str(path), clock=clock, mac_keys=()):
        pass
    assert _ids(path) == {"tr_legacy"}


def test_remaining_traces_stay_valid_with_hmac(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    key = ("k1", secrets.token_bytes(32))
    path = tmp_path / "a.sqlite3"
    clock = _Clock()
    with AuditTraceStore(str(path), clock=clock, mac_keys=(key,)) as store:
        _record(store, "tr_old")
        clock.now = START + timedelta(days=5)
        _record(store, "tr_new")
    monkeypatch.setenv("ATTRACTOR_AUDIT_RETENTION_DAYS", "2")
    with AuditTraceStore(str(path), clock=clock, mac_keys=(key,)) as store:
        assert store.verify_all() == {"valid": 1, "invalid": 0}
    assert _ids(path) == {"tr_new"}
