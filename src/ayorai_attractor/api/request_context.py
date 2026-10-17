"""Request correlation and privacy-preserving structured access logs."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{1,64}\Z")


def _request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name.lower() == b"x-request-id":
            try:
                candidate = value.decode("ascii")
            except UnicodeDecodeError:
                break
            if _REQUEST_ID_PATTERN.fullmatch(candidate):
                return candidate
            break
    return uuid.uuid4().hex


def _route_label(scope: Scope) -> str:
    route = scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else "unmatched"


class RequestContextMiddleware:
    """Return an X-Request-ID and emit one JSON record without payload data."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
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
