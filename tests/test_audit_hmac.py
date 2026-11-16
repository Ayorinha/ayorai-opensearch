"""Keyed MACs authenticate audit traces against writers of the SQLite file.

Threat model: an attacker who can write the database but does not hold
ATTRACTOR_AUDIT_HMAC_KEYS can no longer forge a trace by recomputing the
unkeyed digest. An attacker who holds the key (or controls the service host)
is not covered.
"""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import (
    _R2_V3_FIELDS,
    AuditTraceStore,
    _r2_v3_events,
    audit_mac_keys_from_env,
)
from ayorai_attractor.models import SearchResponse
from ayorai_attractor.replay import ReplayBundle

K1 = ("k1", secrets.token_bytes(32))
K2 = ("k2", secrets.token_bytes(32))


def _record(store: AuditTraceStore, trace_id: str = "tr_m") -> None:
    response = SearchResponse.model_validate(
        {"query": "q", "mode": "balanced", "answer": "a", "trace_id": trace_id}
    )
    store.record(response, AuditReport.from_response(response))


def _forge_finding_count(path: Path, trace_id: str = "tr_m") -> None:
    """Edit a field and recompute the unkeyed digest, as a database writer could."""
    with closing(sqlite3.connect(path)) as connection, connection:
        columns = ", ".join(_R2_V3_FIELDS)
        row = connection.execute(
            f"SELECT {columns} FROM audit_traces WHERE trace_id = ?",  # noqa: S608
            (trace_id,),
        ).fetchone()
        fields = dict(zip(_R2_V3_FIELDS, row, strict=True))
        fields["finding_count"] = 0
        digest = ReplayBundle.build(trace_id, _r2_v3_events(fields), version="r2-v3").digest
        connection.execute(
            "UPDATE audit_traces SET finding_count = 0, replay_digest = ? WHERE trace_id = ?",
            (digest, trace_id),
        )


def _set(path: Path, sql: str, trace_id: str = "tr_m") -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(f"UPDATE audit_traces SET {sql} WHERE trace_id = ?", (trace_id,))  # noqa: S608


def test_without_keys_a_recomputed_digest_still_passes(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=()) as store:
        _record(store)
        _forge_finding_count(path)
        assert store.verify("tr_m") == "valid"  # the documented limit of an unkeyed digest


def test_with_a_key_a_recomputed_digest_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store)
        assert store.verify("tr_m") == "valid"
        _forge_finding_count(path)
        assert store.verify("tr_m") == "invalid"


def test_mac_sealed_trace_fails_closed_when_verification_keys_are_missing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store)
        assert store.verify("tr_m") == "valid"

    # Removing the key configuration must not silently downgrade a signed trace
    # to digest-only verification.
    with AuditTraceStore(str(path), mac_keys=()) as store:
        assert store.verify("tr_m") == "invalid"


@pytest.mark.parametrize(
    "tamper",
    [
        "replay_mac = NULL",  # downgrade: drop the MAC
        "mac_key_id = NULL",
        "mac_key_id = 'unknown'",
        "replay_mac = CASE substr(replay_mac, 1, 1) WHEN '0' THEN '1' ELSE '0' END"
        " || substr(replay_mac, 2)",
    ],
)
def test_mac_tampering_is_detected(tmp_path: Path, tamper: str) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store)
        _set(path, tamper)
        assert store.verify("tr_m") == "invalid"


def test_rotation_keeps_old_traces_valid_and_seals_new_ones_with_the_active_key(
    tmp_path: Path,
) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store, "tr_old")
    with AuditTraceStore(str(path), mac_keys=(K2, K1)) as store:
        _record(store, "tr_new")
        assert store.verify("tr_old") == "valid"
        assert store.verify("tr_new") == "valid"
    with closing(sqlite3.connect(path)) as connection:
        assert dict(connection.execute("SELECT trace_id, mac_key_id FROM audit_traces")) == {
            "tr_old": "k1",
            "tr_new": "k2",
        }
    with AuditTraceStore(str(path), mac_keys=(K2,)) as store:  # k1 retired
        assert store.verify("tr_old") == "invalid"
        assert store.verify("tr_new") == "valid"


def test_a_wrong_key_with_the_same_id_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store)
    with AuditTraceStore(str(path), mac_keys=(("k1", secrets.token_bytes(32)),)) as store:
        assert store.verify("tr_m") == "invalid"


def test_sealing_existing_traces_skips_tampered_ones(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=()) as store:
        _record(store, "tr_ok")
        _record(store, "tr_bad")
    _set(path, "operation_status = 'failed'", "tr_bad")  # digest no longer matches
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        assert store.verify("tr_ok") == "invalid"  # unsealed while keys are configured
        assert store.seal_unsealed() == 1
        assert store.verify("tr_ok") == "valid"
        assert store.verify("tr_bad") == "invalid"
        assert store.seal_unsealed() == 0
    with AuditTraceStore(str(path), mac_keys=()) as store:
        with pytest.raises(ValueError, match="not configured"):
            store.seal_unsealed()


def test_legacy_r2_v2_traces_are_verified_as_before(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        _record(store)
    legacy = ReplayBundle.build(
        "tr_m",
        [
            {
                "event": "audit.completed",
                "verification": "not_adjudicated",
                "evidence_count": 0,
                "failure_count": 0,
            }
        ],
        version="r2-v2",
    ).digest
    _set(path, f"replay_version = 'r2-v2', replay_digest = '{legacy}', replay_mac = NULL")
    with AuditTraceStore(str(path), mac_keys=(K1,)) as store:
        assert store.verify("tr_m") == "valid"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("k1", "id:hex"),
        ("k1:zz", "hex"),
        ("k1:" + "ab" * 16, "32 bytes"),
        ("bad id:" + "ab" * 32, "unique ids"),
        ("k1:" + "ab" * 32 + ",k1:" + "cd" * 32, "unique ids"),
    ],
)
def test_invalid_key_configuration_is_refused(
    monkeypatch: pytest.MonkeyPatch, value: str, message: str
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUDIT_HMAC_KEYS", value)
    with pytest.raises(ValueError, match=message):
        audit_mac_keys_from_env()


def test_keys_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_AUDIT_HMAC_KEYS", "k2:" + "ab" * 32 + ", k1:" + "cd" * 32)
    assert [key_id for key_id, _ in audit_mac_keys_from_env()] == ["k2", "k1"]
    monkeypatch.setenv("ATTRACTOR_AUDIT_HMAC_KEYS", "")
    assert audit_mac_keys_from_env() == ()


def test_sealing_uses_the_active_key(tmp_path: Path) -> None:
    path = tmp_path / "a.sqlite3"
    with AuditTraceStore(str(path), mac_keys=()) as store:
        _record(store)
    with AuditTraceStore(str(path), mac_keys=(K2, K1)) as store:
        assert store.seal_unsealed() == 1
        assert store.verify("tr_m") == "valid"
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT mac_key_id FROM audit_traces").fetchone() == ("k2",)
