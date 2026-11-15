"""Admission control for CPU-bound routes (HTTP 503 + Retry-After beyond the limit)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ayorai_attractor.api.load_control import (
    HEAVY_PATHS,
    HeavyRouteConcurrencyLimitMiddleware,
    max_inflight_from_env,
)


class _Gate:
    """Inner ASGI app that blocks until released, so requests stay in flight."""

    def __init__(self, fail: bool = False) -> None:
        self.release = asyncio.Event()
        self.started = 0
        self.fail = fail

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.started += 1
        await self.release.wait()
        if self.fail:
            raise RuntimeError("handler failure")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


async def _until(condition: Any) -> None:
    while not condition():
        await asyncio.sleep(0)


async def _call(app: Any, path: str) -> tuple[int, dict[bytes, bytes]]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    # A bounded wait turns a broken limiter (request let through to the blocked
    # handler) into a test failure instead of a hang.
    await asyncio.wait_for(
        app({"type": "http", "path": path, "method": "POST", "headers": []}, receive, send),
        timeout=5,
    )
    start = next(m for m in messages if m["type"] == "http.response.start")
    return start["status"], dict(start.get("headers", []))


def test_requests_beyond_the_limit_get_503_with_retry_after() -> None:
    async def scenario() -> None:
        gate = _Gate()
        app = HeavyRouteConcurrencyLimitMiddleware(gate, max_inflight=2)
        first = asyncio.create_task(_call(app, "/v1/check"))
        second = asyncio.create_task(_call(app, "/v1/verify"))
        await asyncio.wait_for(_until(lambda: gate.started >= 2), timeout=5)
        status, headers = await _call(app, "/v1/check")
        assert status == 503
        assert headers[b"retry-after"] == b"1"
        assert gate.started == 2  # the rejected request never reached the handler
        assert app.rejected == 1
        gate.release.set()
        assert (await first)[0] == 200
        assert (await second)[0] == 200
        assert app.inflight == 0
        assert (await _call(app, "/v1/check"))[0] == 200  # capacity is back

    asyncio.run(scenario())


def test_slot_is_released_when_the_handler_raises() -> None:
    async def scenario() -> None:
        gate = _Gate(fail=True)
        gate.release.set()
        app = HeavyRouteConcurrencyLimitMiddleware(gate, max_inflight=1)
        with pytest.raises(RuntimeError):
            await _call(app, "/v1/check")
        assert app.inflight == 0

    asyncio.run(scenario())


def test_light_routes_are_never_limited() -> None:
    async def scenario() -> None:
        gate = _Gate()
        app = HeavyRouteConcurrencyLimitMiddleware(gate, max_inflight=1)
        busy = asyncio.create_task(_call(app, "/v1/check"))
        await asyncio.wait_for(_until(lambda: gate.started >= 1), timeout=5)
        gate.release.set()
        for path in ("/health", "/v1/audit/tr_example", "/docs"):
            assert (await _call(app, path))[0] == 200
        await busy

    asyncio.run(scenario())


def test_every_post_verification_route_is_heavy() -> None:
    from ayorai_attractor.api.app import app

    post_routes = {
        route.path
        for route in app.routes
        if "POST" in getattr(route, "methods", set()) and route.path.startswith("/v1/")
    }
    assert post_routes == HEAVY_PATHS


@pytest.mark.parametrize("value", ["0", "-1", "two", ""])
def test_invalid_limit_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("ATTRACTOR_MAX_INFLIGHT_HEAVY", value)
    with pytest.raises(ValueError, match="positive integer"):
        max_inflight_from_env()


def test_default_limit_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTRACTOR_MAX_INFLIGHT_HEAVY", raising=False)
    assert max_inflight_from_env() == 2
    monkeypatch.setenv("ATTRACTOR_MAX_INFLIGHT_HEAVY", "6")
    assert max_inflight_from_env() == 6


def test_api_refuses_to_start_with_an_invalid_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from ayorai_attractor.api.app import app

    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_MAX_INFLIGHT_HEAVY", "0")
    with pytest.raises(ValueError, match="ATTRACTOR_MAX_INFLIGHT_HEAVY"):
        with TestClient(app):
            pass
