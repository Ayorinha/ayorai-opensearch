"""ADR-012: key scopes, expiry and revocation without restart (DEC-031)."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ayorai_attractor.api import keys as keys_module
from ayorai_attractor.api.auth import (
    PRINCIPAL_STATE_KEY,
    APIKeyAuthMiddleware,
    validate_auth_configuration,
)
from ayorai_attractor.api.http_metrics import http_metrics
from ayorai_attractor.api.keys import (
    SCHEMA,
    SCOPES,
    KeyRegistry,
    RegistryError,
    parse_registry,
    required_scope,
)

PEPPER = "ab" * 32
ROUTES = [
    ("POST", "/v1/check", "verify"),
    ("POST", "/v1/fields", "verify"),
    ("POST", "/v1/verify", "verify"),
    ("POST", "/v1/opensearch", "verify"),
    ("POST", "/v1/audit", "audit:write"),
    ("POST", "/v2/audit", "audit:write"),
    ("GET", "/v1/audit/abc123", "audit:read"),
    ("GET", "/v1/verify/log", "audit:read"),
    ("GET", "/metrics", "metrics"),
]


def _digest(key: str) -> str:
    return hmac.new(bytes.fromhex(PEPPER), key.encode(), hashlib.sha256).hexdigest()


def _key() -> str:
    return secrets.token_urlsafe(32)


def _entry(key_id: str, key: str, scopes: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "id": key_id,
        "digest": _digest(key),
        "scopes": scopes,
        "expires_at": extra.get("expires_at"),
        "revoked_at": extra.get("revoked_at"),
        "revoked_by": extra.get("revoked_by"),
    }


def _write(path: Path, entries: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema": SCHEMA, "keys": entries}))
    os.replace(tmp, path)


def _app() -> FastAPI:
    app = FastAPI()

    def probe(request: Request) -> dict[str, Any]:
        return {"principal": getattr(request.state, PRINCIPAL_STATE_KEY, None)}

    for method, path, _ in ROUTES:
        app.add_api_route(path.replace("abc123", "{trace_id}"), probe, methods=[method])
    app.add_api_route("/openapi-probe", probe, methods=["GET"])
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


def _call(client: TestClient, method: str, path: str, key: str) -> int:
    return client.request(method, path, headers={"X-API-Key": key}).status_code


# --- route table -------------------------------------------------------------


@pytest.mark.parametrize(("method", "path", "scope"), ROUTES)
def test_route_scope_table(method: str, path: str, scope: str) -> None:
    assert required_scope(method, path) == scope
    assert required_scope(method, path + "/") == scope


def test_unlisted_routes_need_no_scope() -> None:
    assert required_scope("GET", "/openapi.json") is None
    assert required_scope("GET", "/v1/check") is None  # wrong method: 405 later, no scope leak
    assert required_scope("HEAD", "/metrics") == "metrics"


# --- criterion 1: negative tests per scope, expiry, revocation, unknown ----


@pytest.mark.parametrize("scope", sorted(SCOPES))
def test_each_scope_opens_only_its_routes(key_file: Path, scope: str) -> None:
    key = _key()
    _write(key_file, [_entry("only", key, [scope])])
    client = TestClient(_app())
    for method, path, needed in ROUTES:
        expected = 200 if needed == scope else 403
        assert _call(client, method, path, key) == expected, (scope, path)
    assert _call(client, "GET", "/openapi-probe", key) == 200


def test_expired_revoked_and_unknown_keys_get_401(key_file: Path) -> None:
    expired, revoked, valid = _key(), _key(), _key()
    _write(
        key_file,
        [
            _entry("expired", expired, ["verify"], expires_at="2000-01-01T00:00:00Z"),
            _entry(
                "revoked",
                revoked,
                ["verify"],
                revoked_at="2001-01-01T00:00:00Z",
                revoked_by="maintainer",
            ),
            _entry("valid", valid, ["verify"], expires_at="2999-01-01T00:00:00Z"),
        ],
    )
    client = TestClient(_app())
    for key in (expired, revoked, _key()):
        response = client.post("/v1/check", headers={"X-API-Key": key})
        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}
    assert _call(client, "POST", "/v1/check", valid) == 200


def test_missing_scope_is_403_not_401(key_file: Path) -> None:
    key = _key()
    _write(key_file, [_entry("reader", key, ["audit:read"])])
    response = TestClient(_app()).post("/v1/verify", headers={"X-API-Key": key})
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


# --- criterion 2: revocation without restart --------------------------------


def test_revocation_applies_without_restart(key_file: Path, caplog: Any) -> None:
    key = _key()
    _write(key_file, [_entry("ops", key, ["verify"])])
    client = TestClient(_app())
    assert _call(client, "POST", "/v1/check", key) == 200
    assert (
        keys_module.main(["revoke", "--file", str(key_file), "--id", "ops", "--by", "Anderson"])
        == 0
    )
    with caplog.at_level("WARNING", logger="ayorai_attractor.api.keys"):
        assert _call(client, "POST", "/v1/check", key) == 401
    assert any("ops revoked by Anderson" in record.getMessage() for record in caplog.records)
    stored = json.loads(key_file.read_text())["keys"][0]
    assert stored["revoked_by"] == "Anderson" and stored["revoked_at"] is not None


def test_new_key_and_scope_change_apply_without_restart(key_file: Path) -> None:
    first, second = _key(), _key()
    _write(key_file, [_entry("a", first, ["verify"])])
    client = TestClient(_app())
    assert _call(client, "POST", "/v1/check", second) == 401
    assert _call(client, "GET", "/metrics", first) == 403
    _write(key_file, [_entry("a", first, ["verify", "metrics"]), _entry("b", second, ["verify"])])
    assert _call(client, "POST", "/v1/check", second) == 200
    assert _call(client, "GET", "/metrics", first) == 200


def test_reload_is_rate_limited(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    _write(path, [_entry("a", _key(), ["verify"])])
    now = [0.0]
    registry = KeyRegistry(str(path), interval=5.0, clock=lambda: now[0])
    _write(path, [])
    now[0] = 4.0
    assert len(registry.current()) == 1
    now[0] = 5.0
    assert registry.current() == ()


# --- criterion 3: invalid file -----------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        json.dumps({"schema": "other", "keys": []}),
        json.dumps({"schema": SCHEMA, "keys": [{"id": "x"}]}),
    ],
)
def test_invalid_file_at_startup_refuses_to_start(key_file: Path, content: str) -> None:
    key_file.write_text(content)
    with pytest.raises(RegistryError):
        validate_auth_configuration()
    with pytest.raises(RegistryError):
        TestClient(_app()).get("/metrics")


def test_missing_file_at_startup_refuses_to_start(key_file: Path) -> None:
    with pytest.raises(RegistryError):
        validate_auth_configuration()


def test_invalid_file_later_keeps_last_valid_and_counts(key_file: Path, caplog: Any) -> None:
    key = _key()
    _write(key_file, [_entry("ops", key, ["verify"])])
    client = TestClient(_app())
    assert _call(client, "POST", "/v1/check", key) == 200  # registry loaded
    before = http_metrics.render()
    key_file.write_text('{"schema": "ayorai.api-keys.v1", "keys": [')  # broken edit
    with caplog.at_level("ERROR", logger="ayorai_attractor.api.keys"):
        assert _call(client, "POST", "/v1/check", key) == 200
    after = http_metrics.render()

    def failures(text: str) -> int:
        line = next(x for x in text.splitlines() if x.startswith("attractor_api_keys_reload"))
        return int(line.split()[-1])

    assert failures(after) == failures(before) + 1
    assert any("keeping last valid" in record.getMessage() for record in caplog.records)
    # Once the file is valid again, it takes effect.
    _write(key_file, [_entry("ops", key, ["metrics"])])
    assert _call(client, "POST", "/v1/check", key) == 403


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda e: e.update(scopes=["admin"]), "scopes"),
        (lambda e: e.update(scopes=[]), "scopes"),
        (lambda e: e.update(scopes=["verify", "verify"]), "scopes"),
        (lambda e: e.update(digest="A" * 64), "digest"),
        (lambda e: e.update(id="Has Space"), "id"),
        (lambda e: e.update(expires_at="2027-01-01"), "expires_at"),
        (lambda e: e.update(expires_at="2027-02-30T00:00:00Z"), "expires_at"),
        (lambda e: e.update(revoked_at="2027-01-01T00:00:00Z"), "revoked"),
        (lambda e: e.update(extra=1), "exactly"),
    ],
)
def test_registry_validation(mutate: Any, message: str) -> None:
    entry = _entry("a", _key(), ["verify"])
    mutate(entry)
    with pytest.raises(RegistryError, match=message):
        parse_registry(json.dumps({"schema": SCHEMA, "keys": [entry]}).encode())


def test_duplicates_are_rejected() -> None:
    key = _key()
    same_digest = [_entry("a", key, ["verify"]), _entry("b", key, ["verify"])]
    same_id = [_entry("a", _key(), ["verify"]), _entry("a", _key(), ["verify"])]
    for entries in (same_digest, same_id):
        with pytest.raises(RegistryError, match="duplicated"):
            parse_registry(json.dumps({"schema": SCHEMA, "keys": entries}).encode())
    raw = '{"schema": "ayorai.api-keys.v1", "schema": "x", "keys": []}'
    with pytest.raises(RegistryError, match="duplicated"):
        parse_registry(raw.encode())


def test_both_sources_is_a_configuration_error(key_file: Path, monkeypatch: Any) -> None:
    _write(key_file, [_entry("a", _key(), ["verify"])])
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="not both"):
        validate_auth_configuration()


# --- criteria 4 and 5: legacy mode unchanged, same principal -----------------


def test_principal_is_the_same_in_legacy_and_file_modes(key_file: Path, monkeypatch: Any) -> None:
    key = _key()
    _write(key_file, [_entry("ops", key, sorted(SCOPES))])
    from_file = TestClient(_app()).post("/v1/check", headers={"X-API-Key": key}).json()
    monkeypatch.delenv("ATTRACTOR_API_KEYS_FILE")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key))
    legacy_client = TestClient(_app())
    from_env = legacy_client.post("/v1/check", headers={"X-API-Key": key}).json()
    assert from_file == from_env and from_env["principal"].startswith("key:")
    # Legacy keys keep every scope.
    for method, path, _ in ROUTES:
        assert _call(legacy_client, method, path, key) == 200


# --- criterion 6: nothing secret leaks ---------------------------------------


def test_no_digest_or_key_in_logs_or_metrics(key_file: Path, caplog: Any, monkeypatch: Any) -> None:
    key = _key()
    _write(key_file, [_entry("ops", key, ["verify"])])
    with caplog.at_level("DEBUG"):
        client = TestClient(_app())
        _call(client, "POST", "/v1/check", key)
        key_file.write_text("{broken")
        _call(client, "POST", "/v1/check", key)
        monkeypatch.setattr("sys.stdin", io.StringIO(_key() + "\n"))
        with pytest.raises(SystemExit, match="invalid key file"):
            keys_module.main(["new", "--id", "next", "--scope", "verify", "--file", str(key_file)])
    text = "\n".join(record.getMessage() for record in caplog.records) + http_metrics.render()
    assert _digest(key) not in text and key not in text and PEPPER not in text


# --- command line --------------------------------------------------------------


def test_new_command_reads_the_key_and_stores_only_its_digest(
    key_file: Path, capsys: Any, monkeypatch: Any
) -> None:
    _write(key_file, [])
    key = _key()
    monkeypatch.setattr("sys.stdin", io.StringIO(key + "\n"))
    arguments = ["new", "--id", "metrics-bot", "--scope", "metrics"]
    arguments += ["--expires", "2999-01-01T00:00:00Z", "--file", str(key_file)]
    assert keys_module.main(arguments) == 0
    captured = capsys.readouterr()
    assert key not in captured.out + captured.err  # never displayed
    stored = json.loads(key_file.read_text())["keys"]
    assert stored[0]["digest"] == _digest(key) and key not in key_file.read_text()
    client = TestClient(_app())
    assert _call(client, "GET", "/metrics", key) == 200
    assert _call(client, "POST", "/v1/check", key) == 403


def test_new_command_rejects_a_short_key(key_file: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
    with pytest.raises(SystemExit, match="at least"):
        keys_module.main(["new", "--id", "x", "--scope", "verify", "--file", "unused.json"])


def test_new_command_refuses_a_terminal(key_file: Path, monkeypatch: Any) -> None:
    class Terminal(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", Terminal(_key() + "\n"))
    with pytest.raises(SystemExit, match="pipe the API key"):
        keys_module.main(["new", "--id", "x", "--scope", "verify", "--file", str(key_file)])


def test_revoke_unknown_or_twice_fails(key_file: Path) -> None:
    _write(key_file, [_entry("a", _key(), ["verify"])])
    with pytest.raises(SystemExit, match="no key"):
        keys_module.main(["revoke", "--file", str(key_file), "--id", "b", "--by", "x"])
    keys_module.main(["revoke", "--file", str(key_file), "--id", "a", "--by", "x"])
    with pytest.raises(SystemExit, match="already revoked"):
        keys_module.main(["revoke", "--file", str(key_file), "--id", "a", "--by", "x"])
