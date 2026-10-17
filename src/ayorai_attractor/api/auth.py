"""Optional API-key authentication for the HTTP API."""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Iterable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def _load_configuration() -> tuple[str, tuple[str, ...], bytes | None]:
    mode = os.getenv("ATTRACTOR_AUTH_MODE", "off").strip().lower()
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
    """Return a keyed digest so a leaked digest list alone cannot verify guesses."""
    return hmac.new(pepper, presented_key.encode("utf-8"), hashlib.sha256).hexdigest()


def validate_auth_configuration() -> None:
    """Validate auth environment settings during application startup."""
    _load_configuration()


class APIKeyAuthMiddleware:
    """Authenticate HTTP requests with keyed HMAC-SHA-256 digests of API keys.

    Authentication is disabled by default. In api_key mode, configure
    ATTRACTOR_API_KEYS_HMAC_SHA256 with comma-separated HMAC-SHA-256 hex digests
    and ATTRACTOR_API_KEY_PEPPER with a separately managed 32-byte secret.
    Raw API keys are never read from configuration or written to logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.mode, self.key_hashes, self.pepper = _load_configuration()

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

        # API keys must be high-entropy bearer tokens, not human passwords.
        # A separate pepper means a leaked digest list alone cannot verify guesses.
        if self.pepper is None:
            await self._unauthorized(scope, receive, send)
            return
        presented_digest = _api_key_digest(presented_key, self.pepper)
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
