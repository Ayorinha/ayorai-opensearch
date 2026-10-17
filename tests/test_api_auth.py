"""Tests for optional API-key authentication."""

import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ayorai_attractor.api.auth import APIKeyAuthMiddleware


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


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def test_authentication_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTRACTOR_AUTH_MODE", raising=False)
    monkeypatch.delenv("ATTRACTOR_API_KEYS_SHA256", raising=False)

    with _client() as client:
        response = client.get("/private")

    assert response.status_code == 200


def test_api_key_mode_rejects_missing_or_invalid_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_SHA256", _digest("correct-secret"))

    with _client() as client:
        missing = client.get("/private")
        invalid = client.get("/private", headers={"Authorization": "Bearer wrong-secret"})

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"detail": "Unauthorized"}
    assert invalid.json() == {"detail": "Unauthorized"}


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer correct-secret"},
        {"X-API-Key": "correct-secret"},
    ],
)
def test_api_key_mode_accepts_bearer_and_x_api_key(
    monkeypatch: pytest.MonkeyPatch,
    header: dict[str, str],
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_SHA256", _digest("correct-secret"))

    with _client() as client:
        response = client.get("/private", headers=header)

    assert response.status_code == 200
    assert response.json() == {"access": "granted"}


def test_health_endpoint_remains_public_in_api_key_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEYS_SHA256", _digest("correct-secret"))

    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_key_mode_requires_at_least_one_configured_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.delenv("ATTRACTOR_API_KEYS_SHA256", raising=False)

    with pytest.raises(ValueError, match="must contain at least one SHA-256 digest"):
        with _client() as client:
            client.get("/private")


@pytest.mark.parametrize(
    ("mode", "configured_hashes", "message"),
    [
        ("unsupported", _digest("secret"), "ATTRACTOR_AUTH_MODE must be"),
        ("api_key", "not-a-hash", "must contain only SHA-256 hex digests"),
    ],
)
def test_invalid_auth_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    configured_hashes: str,
    message: str,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", mode)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_SHA256", configured_hashes)

    with pytest.raises(ValueError, match=message):
        with _client() as client:
            client.get("/private")
