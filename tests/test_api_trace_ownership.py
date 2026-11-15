"""Audit traces belong to the API key that created them (cross-tenant isolation).

A trace_id is an identifier, not a credential: another authenticated key gets the
same 404 as for an unknown trace. Legacy traces recorded before schema v3 have no
owner and stay readable by any authenticated key.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api.auth import APIKeyAuthMiddleware, principal_for_digest
from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import SearchResponse

SEARCH = {"query": "receita da Vértice em 2024"}


def _digest(key: str, pepper_hex: str) -> str:
    return hmac.new(bytes.fromhex(pepper_hex), key.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.fixture
def tenants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> dict[str, Any]:
    pepper = secrets.token_hex(32)
    key_a, key_b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", pepper)
    monkeypatch.setenv(
        "ATTRACTOR_API_KEYS_HMAC_SHA256", f"{_digest(key_a, pepper)},{_digest(key_b, pepper)}"
    )
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    # Starlette caches the middleware stack on first use; rebuild it for this
    # test's keys (monkeypatch restores the cached stack afterwards).
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    client = TestClient(APIKeyAuthMiddleware(app_module.app))
    return {
        "client": client,
        "store": store,
        "path": tmp_path / "audit.sqlite3",
        "a": {"Authorization": f"Bearer {key_a}"},
        "b": {"Authorization": f"Bearer {key_b}"},
        "principal_a": principal_for_digest(_digest(key_a, pepper)),
        "principal_b": principal_for_digest(_digest(key_b, pepper)),
        "keys": (key_a, key_b),
        "digests": (_digest(key_a, pepper), _digest(key_b, pepper)),
    }


def _create(t: dict[str, Any], who: str) -> str:
    response = t["client"].post("/v1/audit", json=SEARCH, headers=t[who])
    assert response.status_code == 200, response.text
    trace_id = response.json()["trace_id"]
    assert isinstance(trace_id, str)
    return trace_id


def test_a_trace_is_readable_by_its_owner_only(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    trace_id = _create(tenants, "a")
    assert client.get(f"/v1/audit/{trace_id}", headers=tenants["a"]).status_code == 200
    other = client.get(f"/v1/audit/{trace_id}", headers=tenants["b"])
    unknown = client.get("/v1/audit/tr_doesnotexist", headers=tenants["b"])
    assert other.status_code == unknown.status_code == 404
    assert other.json() == unknown.json()  # no existence oracle
    assert client.get(f"/v1/audit/{trace_id}").status_code == 401


def test_each_key_sees_only_its_own_traces(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    mine_a = [_create(tenants, "a") for _ in range(3)]
    mine_b = [_create(tenants, "b") for _ in range(3)]
    for trace_id in mine_a:
        assert client.get(f"/v1/audit/{trace_id}", headers=tenants["a"]).status_code == 200
        assert client.get(f"/v1/audit/{trace_id}", headers=tenants["b"]).status_code == 404
    for trace_id in mine_b:
        assert client.get(f"/v1/audit/{trace_id}", headers=tenants["b"]).status_code == 200
        assert client.get(f"/v1/audit/{trace_id}", headers=tenants["a"]).status_code == 404


def test_the_owner_is_stored_and_bound_by_the_digest(tenants: dict[str, Any]) -> None:
    client = tenants["client"]
    trace_id = _create(tenants, "a")
    with closing(sqlite3.connect(tenants["path"])) as connection, connection:
        owner = connection.execute(
            "SELECT owner FROM audit_traces WHERE trace_id = ?", (trace_id,)
        ).fetchone()[0]
        assert owner == tenants["principal_a"]
        # Reassigning the trace to another tenant is detected by r2-v3.
        connection.execute(
            "UPDATE audit_traces SET owner = ? WHERE trace_id = ?",
            (tenants["principal_b"], trace_id),
        )
    stolen = client.get(f"/v1/audit/{trace_id}", headers=tenants["b"])
    assert stolen.status_code == 200
    assert stolen.json()["replay_integrity"] == "invalid"
    assert client.get(f"/v1/audit/{trace_id}", headers=tenants["a"]).status_code == 404


def test_legacy_traces_without_owner_stay_readable(tenants: dict[str, Any]) -> None:
    response = SearchResponse.model_validate(
        {"query": "q", "mode": "balanced", "answer": "a", "trace_id": "tr_legacy"}
    )
    tenants["store"].record(response, AuditReport.from_response(response))  # owner=None
    client = tenants["client"]
    for who in ("a", "b"):
        assert client.get("/v1/audit/tr_legacy", headers=tenants[who]).status_code == 200


def test_the_principal_reveals_neither_key_nor_digest(tenants: dict[str, Any]) -> None:
    principal_a, principal_b = tenants["principal_a"], tenants["principal_b"]
    assert principal_a != principal_b
    assert principal_a.startswith("key:") and len(principal_a) == 20
    for secret in (*tenants["keys"], *tenants["digests"]):
        assert secret not in principal_a and principal_a[4:] not in secret


def test_without_authentication_traces_have_no_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> None:
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    client = TestClient(app_module.app)
    trace_id = client.post("/v1/audit", json=SEARCH).json()["trace_id"]
    assert client.get(f"/v1/audit/{trace_id}").status_code == 200
    with closing(sqlite3.connect(tmp_path / "audit.sqlite3")) as connection:
        assert connection.execute(
            "SELECT owner FROM audit_traces WHERE trace_id = ?", (trace_id,)
        ).fetchone() == (None,)


def test_a_schema_v2_database_is_upgraded_in_place(tmp_path: Path) -> None:
    path = tmp_path / "v2.sqlite3"
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE audit_traces (
                trace_id TEXT PRIMARY KEY, legacy_verification TEXT, verification TEXT,
                operation_status TEXT NOT NULL, evidence_count INTEGER NOT NULL,
                independent_evidence_count INTEGER NOT NULL,
                verified_evidence_count INTEGER NOT NULL, failure_count INTEGER NOT NULL,
                finding_count INTEGER NOT NULL, replay_digest TEXT NOT NULL,
                replay_version TEXT NOT NULL, schema_version INTEGER NOT NULL
            )
            """
        )
        from ayorai_attractor.replay import ReplayBundle

        digest = ReplayBundle.build(
            "tr_v2",
            [
                {
                    "event": "audit.completed",
                    "verification": "not_adjudicated",
                    "evidence_count": 1,
                    "failure_count": 0,
                }
            ],
            version="r2-v2",
        ).digest
        connection.execute(
            "INSERT INTO audit_traces VALUES "
            "('tr_v2', NULL, NULL, 'completed', 1, 0, 0, 0, 1, ?, 'r2-v2', 2)",
            (digest,),
        )
        connection.execute("PRAGMA user_version = 2")
    for _ in range(2):  # idempotent: reopening does not fail or change the row
        with AuditTraceStore(str(path)) as store:
            saved = store.get("tr_v2", requester="key:0000000000000000")
            assert saved is not None and saved.replay_integrity == "valid"
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (3,)
        assert connection.execute(
            "SELECT owner, schema_version FROM audit_traces WHERE trace_id = 'tr_v2'"
        ).fetchone() == (None, 2)
