"""Admission control for CPU-bound routes.

The verification routes run synchronous, CPU-bound work in the worker's thread
pool. Without a bound, every accepted request queues behind the others: in the
2026-11-15 load test (one worker, 16 clients sending 2 MB /v1/check bodies) the
median latency reached 31 s and resident memory 1.6 GiB, because every request
held its parsed documents while waiting. Rejecting work beyond a small number of
in-flight requests keeps latency and memory bounded and tells clients when to
retry (HTTP 503 with ``Retry-After``).

The limit is per worker process; multi-worker or multi-replica deployments get
one limit per process and should still enforce a global limit at a gateway.
The counter is only touched on the event loop, with no ``await`` between the
check and the increment, so no lock is needed.
"""

from __future__ import annotations

import os

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

DEFAULT_MAX_INFLIGHT = 2
HEAVY_PATHS = frozenset({"/v1/check", "/v1/fields", "/v1/verify", "/v1/audit", "/v1/opensearch"})
RETRY_AFTER_SECONDS = 1


def max_inflight_from_env() -> int:
    """Read ATTRACTOR_MAX_INFLIGHT_HEAVY; reject anything but a positive integer."""
    raw = os.getenv("ATTRACTOR_MAX_INFLIGHT_HEAVY", str(DEFAULT_MAX_INFLIGHT)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("ATTRACTOR_MAX_INFLIGHT_HEAVY must be a positive integer") from exc
    if value <= 0:
        raise ValueError("ATTRACTOR_MAX_INFLIGHT_HEAVY must be a positive integer")
    return value


class HeavyRouteConcurrencyLimitMiddleware:
    """Reject heavy requests beyond a per-process in-flight limit with 503."""

    def __init__(self, app: ASGIApp, max_inflight: int | None = None) -> None:
        self.app = app
        self.max_inflight = max_inflight if max_inflight is not None else max_inflight_from_env()
        if self.max_inflight <= 0:
            raise ValueError("max_inflight must be a positive integer")
        self.inflight = 0
        self.rejected = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in HEAVY_PATHS:
            await self.app(scope, receive, send)
            return
        if self.inflight >= self.max_inflight:
            self.rejected += 1
            response = JSONResponse(
                status_code=503,
                content={"detail": "Server busy; retry later"},
                headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
            )
            await response(scope, receive, send)
            return
        self.inflight += 1
        try:
            await self.app(scope, receive, send)
        finally:
            self.inflight -= 1
