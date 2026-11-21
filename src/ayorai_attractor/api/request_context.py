"""Request correlation and privacy-preserving structured access logs."""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ayorai_attractor.api.http_metrics import http_metrics

logger = logging.getLogger(__name__)


def _request_id() -> str:
    """Generate a server-owned correlation ID; never trust a caller-supplied value."""
    return uuid.uuid4().hex


_KNOWN_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/metrics",
        "/v1/opensearch",
        "/v1/audit",
        "/v1/check",
        "/v1/fields",
        "/v1/verify",
        "/v2/audit",
    }
)


def _route_label(scope: Scope) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str):
        return str(route_path)

    # Requests rejected before routing (401, 413, 429) carry no route; label
    # them by path only when the path is a known API route, so arbitrary
    # client-chosen paths never reach the logs.
    path = scope.get("path")
    if path in _KNOWN_PATHS:
        return str(path)
    if (
        isinstance(path, str)
        and path.startswith("/v1/audit/")
        and "/" not in path.removeprefix("/v1/audit/")
    ):
        return "/v1/audit/{trace_id}"
    return "unmatched"


class RequestContextMiddleware:
    """Return a server-generated X-Request-ID and emit one JSON record without payload data."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id()
        # Replace the untrusted inbound header in the ASGI scope as well as
        # the response, so downstream handlers see only the server-owned ID.
        request_headers = [
            (name, value)
            for name, value in scope.get("headers", [])
            if name.lower() != b"x-request-id"
        ]
        request_headers.append((b"x-request-id", request_id.encode("ascii")))
        scope = {**scope, "headers": request_headers}
        method = str(scope.get("method", ""))
        started = time.perf_counter()
        status_code = 500
        logged = False

        def emit() -> None:
            nonlocal logged
            if logged:
                return
            event = {
                "request_id": request_id,
                "method": method,
                "route": _route_label(scope),
                "status": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            logger.info("%s", json.dumps(event, separators=(",", ":"), sort_keys=True))
            http_metrics.observe(
                str(event["route"]), method, status_code, time.perf_counter() - started
            )
            logged = True

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            outgoing = message
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                outgoing = {**message, "headers": headers}
            await send(outgoing)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                emit()

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            status_code = 500
            emit()
            raise
        else:
            emit()
