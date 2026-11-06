"""Regression tests for the API authentication request limiter."""

import hashlib
import hmac
import secrets

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ayorai_attractor.api.auth import APIKeyAuthMiddleware, _FixedWindowRateLimiter


def _digest(key: str, pepper_hex: str) -> str:
    return hmac.new(bytes.fromhex(pepper_hex), key.encode("utf-8"), hashlib.sha256).hexdigest()


def test_fixed_window_limiter_blocks_at_limit_and_resets() -> None:
    limiter = _FixedWindowRateLimiter(limit=2, window_seconds=10, max_clients=4)

    assert limiter.allow("ip:127.0.0.1", now=100) == (True, 0)
    assert limiter.allow("ip:127.0.0.1", now=101) == (True, 0)
    allowed, retry_after = limiter.allow("ip:127.0.0.1", now=102)
    assert allowed is False
    assert retry_after == 8
    assert limiter.allow("ip:127.0.0.1", now=110) == (True, 0)


def test_fixed_window_limiter_evicts_least_recently_used_identity() -> None:
    limiter = _FixedWindowRateLimiter(limit=2, window_seconds=10, max_clients=2)

    assert limiter.allow("ip:a", now=100) == (True, 0)
    assert limiter.allow("ip:b", now=100) == (True, 0)
    assert limiter.allow("ip:a", now=101) == (True, 0)  # a becomes most recently used
    assert limiter.allow("ip:c", now=102) == (True, 0)  # b is evicted
    assert list(limiter._windows) == ["ip:a", "ip:c"]
    assert len(limiter._windows) == 2
    assert limiter._calls == 4


def test_first_request_is_included_in_call_counter() -> None:
    limiter = _FixedWindowRateLimiter(limit=2, window_seconds=10, max_clients=2)

    assert limiter.allow("ip:first", now=100) == (True, 0)
    assert limiter._calls == 1


def test_api_returns_429_and_retry_after_when_ip_limit_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS", "30")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_MAX_CLIENTS", "10")

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    with TestClient(app) as client:
        first = client.get("/private")
        second = client.get("/private")
        third = client.get("/private")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json() == {"detail": "Rate limit exceeded"}
    assert int(third.headers["retry-after"]) > 0


def test_health_endpoint_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "1")

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/private").status_code == 200
        blocked = client.get("/private")

    assert blocked.status_code == 429


def test_rate_limit_rejects_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "0")

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    with pytest.raises(ValueError, match="ATTRACTOR_RATE_LIMIT_REQUESTS must be"):
        with TestClient(app):
            pass


def test_authenticated_key_has_its_own_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = secrets.token_urlsafe(32)
    pepper = secrets.token_hex(32)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", pepper)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key, pepper))
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "2")

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    headers = {"X-API-Key": key}
    for port in (1001, 1002):
        with TestClient(app, client=("127.0.0.1", port)) as client:
            assert client.get("/private", headers=headers).status_code == 200
    with TestClient(app, client=("127.0.0.1", 1003)) as client:
        blocked = client.get("/private", headers=headers)

    assert blocked.status_code == 429


def test_ip_identity_churn_cannot_exhaust_authenticated_key_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = secrets.token_urlsafe(32)
    pepper = secrets.token_hex(32)
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "api_key")
    monkeypatch.setenv("ATTRACTOR_API_KEY_PEPPER", pepper)
    monkeypatch.setenv("ATTRACTOR_API_KEYS_HMAC_SHA256", _digest(key, pepper))
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("ATTRACTOR_RATE_LIMIT_MAX_CLIENTS", "1")

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/private")
    def private() -> dict[str, str]:
        return {"access": "granted"}

    for index in range(1, 8):
        # Separate TestClient instances provide distinct ASGI client IPs.
        with TestClient(app, client=(f"192.0.2.{index}", 1000)) as client:
            response = client.get("/private", headers={"X-API-Key": "invalid"})
            assert response.status_code == 401

    # A new IP still gets through, and its valid key has its own table.
    with TestClient(app, client=("198.51.100.10", 1000)) as client:
        response = client.get("/private", headers={"X-API-Key": key})

    assert response.status_code == 200
