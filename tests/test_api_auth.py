"""Tests for API-key authentication defaults and behavior."""

import hashlib
import hmac
import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ayorai_attractor.api.auth import MIN_API_KEY_LENGTH, APIKeyAuthMiddleware


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    return TestClient(app)


def _digest(key: str, pepper_hex: str) -> str:
    return hmac.new(bytes.fromhex(pepper_hex), key.encode("utf-8"), hashlib.sha256).hexdigest()


def _set_pepper(monkeypatch: pytest.MonkeyPatch) -> str:
    pepper = secrets.token_hex(32)
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", pepper)
    return pepper


def test_authentication_fails_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTRACTOR_AUTH_MODE", raising=False)
    monkeypatch.delenv("ATTRACTOR_API_KEYS_HMAC_SHA256", raising=False)
    monkeypatch.delenv("ATTRACTOR_API_KEY_PEPPER", raising=False)

    with pytest.raises(ValueError, match="ATTRACTOR_API_KEY_PEPPER must be"):
        with _client() as client:
            client.get("/private")


def test_authentication_can_be_disabled_only_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.delenv("ATTRACTOR_API_KEYS_HMAC_SHA256", raising=False)
    monkeypatch.delenv("ATTRACTOR_API_KEY_PEPPER", raising=False)

    with _client() as client:
        response = client.get("/private")

    assert response.status_code == 200


def test_api_key_mode_rejects_missing_or_invalid_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    correct_key = secrets.token_urlsafe(32)
    wrong_key = secrets.token_urlsafe(32)
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(correct_key, pepper))

    with _client() as client:
        missing = client.get("/private")
        invalid = client.get("/private", headers={"Authorization": f"Bearer {wrong_key}"})

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"detail": "Unauthorized"}
    assert invalid.json() == {"detail": "Unauthorized"}


@pytest.mark.parametrize("header_name", ["Authorization", "X-API-Key"])
def test_api_key_mode_accepts_bearer_and_x_api_key(
    monkeypatch: pytest.MonkeyPatch,
    header_name: str,
) -> None:
    key = secrets.token_urlsafe(32)
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key, pepper))
    value = f"Bearer {key}" if header_name == "Authorization" else key

    with _client() as client:
        response = client.get("/private", headers={header_name: value})

    assert response.status_code == 200
    assert response.json() == {"access": "granted"}


def test_health_endpoint_remains_public_in_api_key_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv(
        "ATTRACTOR_API_KEYS_HMAC_SHA256",
        _digest(secrets.token_urlsafe(32), pepper),
    )

    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_key_mode_requires_at_least_one_configured_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.delenv("ATTRACTOR_API_KEYS_HMAC_SHA256", raising=False)

    with pytest.raises(ValueError, match="must contain at least one HMAC-SHA-256 digest"):
        with _client() as client:
            client.get("/private")


def test_api_key_mode_requires_valid_pepper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", "0" * 64)
    monkeypatch.delenv("ATTRACTOR_API_KEY_PEPPER", raising=False)

    with pytest.raises(ValueError, match="ATTRACTOR_API_KEY_PEPPER must be"):
        with _client() as client:
            client.get("/private")


@pytest.mark.parametrize(
    ("mode", "configured_hashes", "message"),
    [
        ("unsupported", "0" * 64, "ATTRACTOR_AUTH_MODE must be"),
        ("api_key", "not-a-hash", "must contain only HMAC-SHA-256 hex digests"),
    ],
)
def test_invalid_auth_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    configured_hashes: str,
    message: str,
) -> None:
    _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", mode)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", configured_hashes)

    with pytest.raises(ValueError, match=message):
        with _client() as client:
            client.get("/private")


def test_api_key_mode_rejects_short_keys_even_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short_key = secrets.token_urlsafe(8)
    assert len(short_key) < MIN_API_KEY_LENGTH
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(short_key, pepper))

    with _client() as client:
        response = client.get("/private", headers={"X-API-Key": short_key})

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


@pytest.mark.parametrize("header_name", ["Authorization", "X-API-Key"])
def test_api_key_mode_rejects_duplicate_credential_headers(
    monkeypatch: pytest.MonkeyPatch,
    header_name: str,
) -> None:
    key = secrets.token_urlsafe(32)
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key, pepper))
    value = f"Bearer {key}" if header_name == "Authorization" else key

    with _client() as client:
        response = client.get(
            "/private",
            headers=[(header_name, value), (header_name, value)],
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_api_key_mode_accepts_any_key_during_rotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_key = secrets.token_urlsafe(32)
    next_key = secrets.token_urlsafe(32)
    pepper = _set_pepper(monkeypatch)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv(
        "ATTRACTOR_API_KEYS_HMAC_SHA256",
        f"{_digest(active_key, pepper)},{_digest(next_key, pepper)}",
    )

    with _client() as client:
        active_response = client.get(
            "/private", headers={"X-API-Key": active_key}
        )
        next_response = client.get(
            "/private", headers={"X-API-Key": next_key}
        )

    assert active_response.status_code == 200
    assert next_response.status_code == 200
