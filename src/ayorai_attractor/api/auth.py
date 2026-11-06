"""API-key authentication and bounded per-client request throttling."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import OrderedDict
from collections.abc import Iterable
from math import ceil

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# API keys are machine-generated bearer tokens, not human passwords.
MIN_API_KEY_LENGTH = 32
_DEFAULT_RATE_LIMIT_REQUESTS = 120
_DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
_DEFAULT_RATE_LIMIT_MAX_CLIENTS = 10_000


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _load_configuration() -> tuple[str, tuple[str, ...], bytes | None]:
    mode = os.getenv("ATTRACTOR_AUTH_MODE", "api_key").strip().lower()
    if mode not in {"off", "api_key"}:
        raise ValueError("ATTRACTOR_AUTH_MODE must be 'off' or 'api_key'")

    configured = os.getenv("ATTRACTOR_API_KEYS_HMAC_SHA256", "")
    hashes = tuple(item.strip().lower() for item in configured.split(",") if item.strip())
    if any(not _is_sha256_hex(item) for item in hashes):
        raise ValueError(
            "ATTRACTOR_API_KEYS_HMAC_SHA256 must contain only HMAC-SHA-256 hex digests"
        )

    pepper_hex = os.getenv("ATTRACTOR_API_KEY_PEPPER", "").strip()
    pepper: bytes | None = None
    if mode == "api_key":
        if not _is_sha256_hex(pepper_hex):
            raise ValueError(
                "ATTRACTOR_API_KEY_PEPPER must be a 32-byte secret encoded as 64 hex characters "
                "when ATTRACTOR_AUTH_MODE=api_key"
            )
        pepper = bytes.fromhex(pepper_hex)
        if not hashes:
            raise ValueError(
                "ATTRACTOR_API_KEYS_HMAC_SHA256 must contain at least one HMAC-SHA-256 digest "
                "when ATTRACTOR_AUTH_MODE=api_key"
            )
    return mode, hashes, pepper


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _api_key_digest(presented_key: str, pepper: bytes) -> str:
    return hmac.new(pepper, presented_key.encode("utf-8"), hashlib.sha256).hexdigest()


def validate_auth_configuration() -> None:
    """Validate auth and throttling environment settings during startup."""
    _load_configuration()
    _positive_int_env("ATTRACTOR_RATE_LIMIT_REQUESTS", _DEFAULT_RATE_LIMIT_REQUESTS)
    _positive_int_env("ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS", _DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
    _positive_int_env("ATTRACTOR_RATE_LIMIT_MAX_CLIENTS", _DEFAULT_RATE_LIMIT_MAX_CLIENTS)


class _FixedWindowRateLimiter:
    """Bounded in-process fixed-window limiter; identities never contain raw credentials."""

    def __init__(self, limit: int, window_seconds: int, max_clients: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._windows: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self._calls = 0

    def allow(self, identity: str, now: float | None = None) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        window = self._windows.get(identity)
        if window is None or current - window[0] >= self.window_seconds:
            self._windows.pop(identity, None)
            if len(self._windows) >= self.max_clients:
                self._prune(current)
            if len(self._windows) >= self.max_clients:
                return False, self.window_seconds
            self._windows[identity] = (current, 1)
            return True, 0

        started, count = window
        if count >= self.limit:
            return False, max(1, ceil(self.window_seconds - (current - started)))
        self._windows[identity] = (started, count + 1)
        self._windows.move_to_end(identity)
        self._calls += 1
        if self._calls % 256 == 0:
            self._prune(current)
        return True, 0

    def _prune(self, now: float) -> None:
        expired = [
            identity
            for identity, (started, _) in self._windows.items()
            if now - started >= self.window_seconds
        ]
        for identity in expired:
            self._windows.pop(identity, None)


class APIKeyAuthMiddleware:
    """Authenticate API keys and apply bounded IP/key request limits.

    Rate limiting is process-local. Multi-worker or multi-replica deployments
    must enforce an additional shared edge/API-gateway limit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.mode, self.key_hashes, self.pepper = _load_configuration()
        self.rate_limiter = _FixedWindowRateLimiter(
            limit=_positive_int_env("ATTRACTOR_RATE_LIMIT_REQUESTS", _DEFAULT_RATE_LIMIT_REQUESTS),
            window_seconds=_positive_int_env(
                "ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS", _DEFAULT_RATE_LIMIT_WINDOW_SECONDS
            ),
            max_clients=_positive_int_env(
                "ATTRACTOR_RATE_LIMIT_MAX_CLIENTS", _DEFAULT_RATE_LIMIT_MAX_CLIENTS
            ),
        )

    @staticmethod
    def _extract_key(headers: Iterable[tuple[bytes, bytes]]) -> str | None:
        normalized: dict[bytes, bytes] = {}
        for name, header_value in headers:
            header_name = name.lower()
            if header_name in {b"authorization", b"x-api-key"} and header_name in normalized:
                return None
            normalized[header_name] = header_value
        if b"authorization" in normalized and b"x-api-key" in normalized:
            return None

        authorization = normalized.get(b"authorization", b"").decode("latin-1").strip()
        if authorization:
            scheme, separator, token = authorization.partition(" ")
            if separator and scheme.lower() == "bearer" and token.strip():
                return token.strip()

        api_key = normalized.get(b"x-api-key")
        if api_key is not None:
            value = api_key.decode("latin-1").strip()
            if value:
                return value
        return None

    @staticmethod
    def _client_identity(scope: Scope) -> str:
        client = scope.get("client")
        if isinstance(client, (tuple, list)) and client:
            return f"ip:{client[0]}"
        return "ip:unknown"

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
        retry_after: int | None = None,
    ) -> None:
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers=headers,
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        allowed, retry_after = self.rate_limiter.allow(self._client_identity(scope))
        if not allowed:
            await self._reject(scope, receive, send, 429, "Rate limit exceeded", retry_after)
            return

        if self.mode == "off":
            await self.app(scope, receive, send)
            return

        presented_key = self._extract_key(scope.get("headers", []))
        if presented_key is None or len(presented_key) < MIN_API_KEY_LENGTH:
            await self._reject(scope, receive, send, 401, "Unauthorized")
            return

        if self.pepper is None:
            await self._reject(scope, receive, send, 401, "Unauthorized")
            return
        presented_digest = _api_key_digest(presented_key, self.pepper)
        matched = False
        for configured_digest in self.key_hashes:
            matched |= hmac.compare_digest(presented_digest, configured_digest)
        if not matched:
            await self._reject(scope, receive, send, 401, "Unauthorized")
            return

        allowed, retry_after = self.rate_limiter.allow(f"key:{presented_digest}")
        if not allowed:
            await self._reject(
                scope, receive, send, 429, "Rate limit exceeded", retry_after
            )
            return

        await self.app(scope, receive, send)
