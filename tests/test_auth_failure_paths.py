"""ADR-012 and ADR-013: failure and abuse paths of key authentication and tenants."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import json
import os
import secrets
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api import keys as keys_module
from ayorai_attractor.api.auth import (
    PRINCIPAL_STATE_KEY,
    TENANT_STATE_KEY,
    APIKeyAuthMiddleware,
    validate_auth_configuration,
)
from ayorai_attractor.api.http_metrics import http_metrics
from ayorai_attractor.api.keys import SCHEMA, RegistryError, parse_registry, reload_interval
from ayorai_attractor.audit_store import AuditTraceStore

PEPPER = "cd" * 32


def _digest(key: str) -> str:
    return hmac.new(bytes.fromhex(PEPPER), key.encode(), hashlib.sha256).hexdigest()


def _entry(key_id: str, key: str, scopes: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "id": key_id,
        "digest": _digest(key),
        "scopes": scopes,
        "expires_at": None,
        "revoked_at": None,
        "revoked_by": None,
        **extra,
    }


def _write(path: Path, entries: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema": SCHEMA, "keys": entries}))
    os.replace(tmp, path)


def _probe_app() -> FastAPI:
    app = FastAPI()

    @app.post("/v1/check")
    def check(request: Request) -> dict[str, Any]:
        return {
            "principal": getattr(request.state, PRINCIPAL_STATE_KEY, None),
            "tenant": getattr(request.state, TENANT_STATE_KEY, None),
        }

    app.add_middleware(APIKeyAuthMiddleware)
    return app


@pytest.fixture
def key_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "keys.json"
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", PEPPER)
    monkeypatch.delenv("ATTRACTOR_API_KEYS_HMAC_SHA256", raising=False)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_FILE", str(path))
    monkeypatch.setenv("ATTRACTOR_API_KEYS_RELOAD_SECONDS", "0.001")
    return path


def _failures() -> int:
    line = next(
        x for x in http_metrics.render().splitlines() if x.startswith("attractor_api_keys_reload")
    )
    return int(line.split()[-1])


# --- the key file disappears or becomes unreadable after startup --------------


def test_deleted_key_file_keeps_the_last_valid_registry(key_file: Path) -> None:
    key = secrets.token_urlsafe(32)
    _write(key_file, [_entry("ops", key, ["verify"])])
    client = TestClient(_probe_app())
    assert client.post("/v1/check", headers={"X-API-Key": key}).status_code == 200
    before = _failures()
    key_file.unlink()
    # A deleted file must not turn into "no keys" (outage) nor into "any key".
    assert client.post("/v1/check", headers={"X-API-Key": key}).status_code == 200
    assert client.post("/v1/check", headers={"X-API-Key": "x" * 43}).status_code == 401
    assert _failures() >= before + 1  # one count per failed reload attempt


# --- registry shape ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ([], "exactly 'schema' and 'keys'"),
        ({"schema": SCHEMA}, "exactly 'schema' and 'keys'"),
        ({"schema": SCHEMA, "keys": [], "extra": 1}, "exactly 'schema' and 'keys'"),
        ({"schema": SCHEMA, "keys": {}}, "must be a list"),
        ({"schema": SCHEMA, "keys": ["not an object"]}, "must have exactly"),
    ],
)
def test_registry_shape_errors(document: object, message: str) -> None:
    with pytest.raises(RegistryError, match=message):
        parse_registry(json.dumps(document).encode())


@pytest.mark.parametrize("revoked_by", ["", "   ", "x" * 129, 7])
def test_revoked_by_must_be_a_short_text(revoked_by: object) -> None:
    entry = _entry(
        "a",
        secrets.token_urlsafe(32),
        ["verify"],
        revoked_at="2026-01-01T00:00:00Z",
        revoked_by=revoked_by,
    )
    with pytest.raises(RegistryError, match="revoked_by"):
        parse_registry(json.dumps({"schema": SCHEMA, "keys": [entry]}).encode())


def test_invalid_utf8_is_refused() -> None:
    with pytest.raises(RegistryError, match="UTF-8 JSON"):
        parse_registry(b"\xff\xfe")


@pytest.mark.parametrize("value", ["abc", "0", "-1", "3601"])
def test_reload_interval_must_be_sane(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ATTRACTOR_API_KEYS_RELOAD_SECONDS", value)
    with pytest.raises(ValueError, match="ATTRACTOR_API_KEYS_RELOAD_SECONDS"):
        reload_interval()


@pytest.mark.parametrize(
    "variable", ["ATTRACTOR_RATE_LIMIT_REQUESTS", "ATTRACTOR_RATE_LIMIT_MAX_CLIENTS"]
)
@pytest.mark.parametrize("value", ["many", "0", "-3"])
def test_rate_limit_settings_must_be_positive_integers(
    key_file: Path, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    _write(key_file, [_entry("a", secrets.token_urlsafe(32), ["verify"])])
    monkeypatch.setenv(variable, value)
    with pytest.raises(ValueError, match=variable):
        validate_auth_configuration()


# --- authenticated-key rate limit ------------------------------------------------


def test_a_key_is_limited_across_client_addresses(
    key_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Spreading one key over many IPs must not escape its own limit.
    key = secrets.token_urlsafe(32)
    _write(key_file, [_entry("ops", key, ["verify"])])
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "2")
    app = _probe_app()

    async def call(address: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app, client=(address, 4000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/check", headers={"X-API-Key": key})

    async def scenario() -> list[httpx.Response]:
        return [await call(f"198.51.100.{n}") for n in range(1, 4)]

    responses = asyncio.run(scenario())
    assert [r.status_code for r in responses] == [200, 200, 429]
    assert int(responses[2].headers["Retry-After"]) >= 1


# --- tenant cannot be chosen by the client ------------------------------------------


def test_the_client_cannot_choose_its_tenant(
    key_file: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: Any
) -> None:
    owner, outsider = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    scopes = ["verify", "audit:write", "audit:read"]
    _write(
        key_file,
        [
            _entry("owner", owner, scopes, tenant="acme"),
            _entry("outsider", outsider, scopes, tenant="beta"),
        ],
    )
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    client = TestClient(APIKeyAuthMiddleware(app_module.app))
    created = client.post(
        "/v1/audit", json={"query": "receita da Vértice"}, headers={"X-API-Key": owner}
    )
    trace_id = created.json()["trace_id"]
    attempts = [
        {"X-Tenant": "acme"},
        {"X-Tenant-Id": "acme"},
        {"Tenant": "acme"},
        {"X-Ayorai-Principal": "key:0000000000000000"},
    ]
    for extra in attempts:
        response = client.get(f"/v1/audit/{trace_id}", headers={"X-API-Key": outsider, **extra})
        assert response.status_code == 404, extra
    for query in ("?tenant=acme", "?tenant_id=acme"):
        response = client.get(f"/v1/audit/{trace_id}{query}", headers={"X-API-Key": outsider})
        assert response.status_code == 404, query


def test_tenant_state_comes_only_from_the_key_file(key_file: Path) -> None:
    key = secrets.token_urlsafe(32)
    _write(key_file, [_entry("ops", key, ["verify"], tenant="acme")])
    body = (
        TestClient(_probe_app())
        .post("/v1/check", headers={"X-API-Key": key, "X-Tenant": "beta"})
        .json()
    )
    assert body["tenant"] == "acme"


# --- command-line failure paths ---------------------------------------------------


def test_new_without_a_pepper_refuses(key_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(key_file, [])
    monkeypatch.delenv("ATTRACTOR_API_KEY_PEPPER")
    monkeypatch.setattr("sys.stdin", io.StringIO(secrets.token_urlsafe(32) + "\n"))
    with pytest.raises(SystemExit, match="PEPPER"):
        keys_module.main(["new", "--id", "a", "--scope", "verify", "--file", str(key_file)])
    assert json.loads(key_file.read_text())["keys"] == []


@pytest.mark.parametrize("key_id", ["Upper", "", "with space", "-dash-first"])
def test_new_with_an_invalid_id_refuses(
    key_file: Path, monkeypatch: pytest.MonkeyPatch, key_id: str
) -> None:
    _write(key_file, [])
    monkeypatch.setattr("sys.stdin", io.StringIO(secrets.token_urlsafe(32) + "\n"))
    with pytest.raises(SystemExit, match="--id"):
        keys_module.main(["new", f"--id={key_id}", "--scope", "verify", "--file", str(key_file)])


def test_new_with_an_invalid_expiry_refuses(
    key_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(key_file, [])
    monkeypatch.setattr("sys.stdin", io.StringIO(secrets.token_urlsafe(32) + "\n"))
    arguments = ["new", "--id", "a", "--scope", "verify", "--expires", "2027-01-01"]
    with pytest.raises(SystemExit, match="invalid key file"):
        keys_module.main([*arguments, "--file", str(key_file)])


def test_a_failed_write_leaves_the_key_file_untouched(
    key_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = secrets.token_urlsafe(32)
    _write(key_file, [_entry("a", key, ["verify"])])
    original = key_file.read_bytes()

    def failing_replace(source: str, destination: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(keys_module.os, "replace", failing_replace)
    with pytest.raises(OSError, match="disk full"):
        keys_module.main(["revoke", "--file", str(key_file), "--id", "a", "--by", "ops"])
    assert key_file.read_bytes() == original
    assert [p.name for p in key_file.parent.iterdir() if p.name.startswith(".keys.json.")] == []
