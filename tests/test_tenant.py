"""ADR-013: tenant distinct from principal (DEC-032)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api import keys as keys_module
from ayorai_attractor.api import verify_log as verify_log_module
from ayorai_attractor.api.auth import APIKeyAuthMiddleware
from ayorai_attractor.api.keys import SCHEMA, RegistryError, parse_registry
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationEvent, VerificationLog, verify_receipt
from tests.test_verify_log import _r2a

SEARCH = {"query": "receita da Vértice em 2024"}
PEPPER = secrets.token_hex(32)


def _digest(key: str) -> str:
    return hmac.new(bytes.fromhex(PEPPER), key.encode(), hashlib.sha256).hexdigest()


def _entry(key_id: str, key: str, scopes: list[str], **extra: Any) -> dict[str, Any]:
    entry = {
        "id": key_id,
        "digest": _digest(key),
        "scopes": scopes,
        "expires_at": None,
        "revoked_at": extra.pop("revoked_at", None),
        "revoked_by": extra.pop("revoked_by", None),
    }
    entry.update(extra)
    return entry


def _write(path: Path, entries: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema": SCHEMA, "keys": entries}))
    os.replace(tmp, path)


ALL = ["verify", "audit:write", "audit:read"]


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: Any) -> dict[str, Any]:
    keys = {name: secrets.token_urlsafe(32) for name in ("a1", "a2", "b1", "a_writer")}
    path = tmp_path / "keys.json"
    _write(
        path,
        [
            _entry("a1", keys["a1"], ALL, tenant="acme"),
            _entry("a2", keys["a2"], ALL, tenant="acme"),
            _entry("b1", keys["b1"], ALL, tenant="beta"),
            _entry("a-writer", keys["a_writer"], ["audit:write"], tenant="acme"),
        ],
    )
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", PEPPER)
    monkeypatch.delenv("ATTRACTOR_API_KEYS_HMAC_SHA256", raising=False)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_FILE", str(path))
    monkeypatch.setenv("ATTRACTOR_API_KEYS_RELOAD_SECONDS", "0.001")
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    client = TestClient(APIKeyAuthMiddleware(app_module.app))
    return {"client": client, "keys": keys, "path": path}


def _h(world: dict[str, Any], who: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {world['keys'][who]}"}


def _create(world: dict[str, Any], who: str) -> str:
    response = world["client"].post("/v1/audit", json=SEARCH, headers=_h(world, who))
    assert response.status_code == 200, response.text
    return str(response.json()["trace_id"])


def _read(world: dict[str, Any], who: str, trace_id: str) -> int:
    return int(world["client"].get(f"/v1/audit/{trace_id}", headers=_h(world, who)).status_code)


# --- criterion 1: same tenant reads, other tenant gets 404 -------------------


def test_same_tenant_reads_other_tenant_gets_404(world: dict[str, Any]) -> None:
    from_a1, from_b1 = _create(world, "a1"), _create(world, "b1")
    assert _read(world, "a1", from_a1) == 200
    assert _read(world, "a2", from_a1) == 200  # colleague in the same tenant
    assert _read(world, "b1", from_a1) == 404  # other tenant
    assert _read(world, "a1", from_b1) == 404 and _read(world, "a2", from_b1) == 404
    unknown = world["client"].get("/v1/audit/tr_doesnotexist", headers=_h(world, "b1"))
    other = world["client"].get(f"/v1/audit/{from_a1}", headers=_h(world, "b1"))
    assert other.json() == unknown.json()  # no existence oracle across tenants


# --- criterion 2: audit:read is still required --------------------------------


def test_reading_needs_audit_read_even_inside_the_tenant(world: dict[str, Any]) -> None:
    trace_id = _create(world, "a1")
    assert _read(world, "a_writer", trace_id) == 403


# --- criterion 3: legacy mode unchanged ----------------------------------------


def test_legacy_mode_keeps_owner_only(monkeypatch: Any, tmp_path: Path, request: Any) -> None:
    key_a, key_b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", PEPPER)
    monkeypatch.delenv("ATTRACTOR_API_KEYS_FILE", raising=False)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", f"{_digest(key_a)},{_digest(key_b)}")
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    client = TestClient(APIKeyAuthMiddleware(app_module.app))
    created = client.post("/v1/audit", json=SEARCH, headers={"X-API-Key": key_a})
    trace_id = created.json()["trace_id"]
    assert client.get(f"/v1/audit/{trace_id}", headers={"X-API-Key": key_a}).status_code == 200
    assert client.get(f"/v1/audit/{trace_id}", headers={"X-API-Key": key_b}).status_code == 404


# --- criterion 4: revoked owner and tenant changes without restart ------------


def test_revoked_owner_traces_stay_readable_by_the_tenant(world: dict[str, Any]) -> None:
    trace_id = _create(world, "a2")
    keys_module.main(["revoke", "--file", str(world["path"]), "--id", "a2", "--by", "ops"])
    assert _read(world, "a2", trace_id) == 401  # the revoked key itself is out
    assert _read(world, "a1", trace_id) == 200  # the tenant keeps its trail


def test_moving_a_key_to_another_tenant_applies_without_restart(world: dict[str, Any]) -> None:
    trace_id = _create(world, "a1")
    assert _read(world, "b1", trace_id) == 404
    document = json.loads(world["path"].read_text())
    for item in document["keys"]:
        if item["id"] == "b1":
            item["tenant"] = "acme"
    _write(world["path"], document["keys"])
    assert _read(world, "b1", trace_id) == 200


# --- criterion 5: tenant in the verify record (v2), v1 receipts still verify --


def test_verify_records_carry_the_tenant_and_old_receipts_verify(
    world: dict[str, Any], monkeypatch: Any, tmp_path: Path
) -> None:
    seed = bytes(range(32))
    origin = "attractor.example/verify-log"
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_MODE", "local")
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_KEY", seed.hex())
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_ORIGIN", origin)
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_DB", str(tmp_path / "v.sqlite3"))
    verify_log_module.close_verify_log()
    try:
        response = world["client"].post("/v1/verify", json=_r2a(), headers=_h(world, "b1"))
        assert response.status_code == 200, response.text
        receipt = response.json()["audit_receipt"]
        assert receipt["record"]["schema"] == "ayorai.verify-record.v2"
        assert receipt["record"]["tenant"] == "beta"
        signer = NoteSigner(origin, seed)
        assert verify_receipt(receipt, signer.verifier_key)
        leaf = json.loads(base64.b64decode(receipt["leaf"]))
        assert "tenant" not in leaf and "beta" not in json.dumps(leaf)  # never public
    finally:
        verify_log_module.close_verify_log()


def test_receipts_with_and_without_tenant_verify_in_one_log(tmp_path: Path) -> None:
    signer = NoteSigner("attractor.example/verify-log", bytes(32))
    with VerificationLog(str(tmp_path / "v.sqlite3"), signer) as log:
        base = dict(
            output_sha256="1" * 64,
            rules_sha256="a" * 64,
            decision_state="DECIDED",
            verdict="SUPPORTED",
            client="c",
            received_at="2026-11-22T00:00:00Z",
            software_id="x",
        )
        default = log.append(VerificationEvent(input_sha256="0" * 64, **base))
        acme = log.append(VerificationEvent(input_sha256="2" * 64, tenant="acme", **base))
        assert default["record"]["tenant"] == "default" and acme["record"]["tenant"] == "acme"
        assert all(verify_receipt(r, signer.verifier_key) for r in (default, acme))
        assert log.verify_log()["valid"]
    with pytest.raises(ValueError, match="tenant"):
        VerificationEvent(input_sha256="0" * 64, tenant="Bad Tenant", **base)


# --- criterion 6: file validation ----------------------------------------------


def test_tenant_field_is_optional_and_validated() -> None:
    key = secrets.token_urlsafe(32)
    without = parse_registry(
        json.dumps({"schema": SCHEMA, "keys": [_entry("a", key, ALL)]}).encode()
    )
    assert without[0].tenant == "default"
    for bad in ("Acme", "", "a b", 7, None, "x" * 65):
        raw = json.dumps({"schema": SCHEMA, "keys": [_entry("a", key, ALL, tenant=bad)]})
        with pytest.raises(RegistryError, match="tenant"):
            parse_registry(raw.encode())


def test_new_command_sets_the_tenant(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "keys.json"
    _write(path, [])
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", PEPPER)
    monkeypatch.setattr("sys.stdin", io.StringIO(secrets.token_urlsafe(32) + "\n"))
    arguments = ["new", "--id", "k", "--scope", "verify", "--tenant", "acme", "--file", str(path)]
    keys_module.main(arguments)
    assert json.loads(path.read_text())["keys"][0]["tenant"] == "acme"
    monkeypatch.setattr("sys.stdin", io.StringIO(secrets.token_urlsafe(32) + "\n"))
    with pytest.raises(SystemExit, match="tenant"):
        keys_module.main(
            ["new", "--id", "j", "--scope", "verify", "--tenant", "ACME", "--file", str(path)]
        )
