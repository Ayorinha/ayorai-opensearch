"""Optional API-key authentication for the HTTP API."""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Iterable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def _load_configuration() -> tuple[str, tuple[str, ...]]:
    mode = os.getenv("ATTRACTOR_AUTH_MODE", "off").strip().lower()
    if mode not in {"off", "api_key"}:
        raise ValueError("ATTRACTOR_AUTH_MODE must be 'off' or 'api_key'")

    configured = os.getenv("ATTRACTOR_API_KEYS_SHA256", "")
    hashes = tuple(item.strip().lower() for item in configured.split(",") if item.strip())
    if any(not _is_sha256_hex(item) for item in hashes):
        raise ValueError("ATTRACTOR_API_KEYS_SHA256 must contain only SHA-256 hex digests")
    if mode == "api_key" and not hashes:
        raise ValueError(
            "ATTRACTOR_API_KEYS_SHA256 must contain at least one SHA-256 digest "
            "when ATTRACTOR_AUTH_MODE=api_key"
        )
    return mode, hashes


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def validate_auth_configuration() -> None:
    """Validate auth environment settings during application startup."""
    _load_configuration()


class APIKeyAuthMiddleware:
    """Authenticate HTTP requests with SHA-256 digests of configured API keys.

    Authentication is disabled by default. In api_key mode, configure
    ATTRACTOR_API_KEYS_SHA256 as a comma-separated list of SHA-256 hex digests.
    Raw API keys are never read from configuration or written to logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.mode, self.key_hashes = _load_configuration()

    @staticmethod
    def _extract_key(headers: Iterable[tuple[bytes, bytes]]) -> str | None:
        normalized = {name.lower(): value for name, value in headers}
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.mode == "off" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        presented_key = self._extract_key(scope.get("headers", []))
        if presented_key is None:
            await self._unauthorized(scope, receive, send)
            return

        presented_digest = hashlib.sha256(presented_key.encode("utf-8")).hexdigest()
        matched = any(
            hmac.compare_digest(presented_digest, configured_digest)
            for configured_digest in self.key_hashes
        )
        if not matched:
            await self._unauthorized(scope, receive, send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _unauthorized(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        await response(scope, receive, send)
