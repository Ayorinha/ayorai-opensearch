"""Admission control for CPU-bound routes (HTTP 503 + Retry-After beyond the limit)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
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
        if "POST" in getattr(route, "methods", set()) and route.path.startswith(("/v1/", "/v2/"))
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


def test_limiter_is_installed_between_authentication_and_body_limit() -> None:
    """The real application wires the limiter: after authentication, before body buffering.

    ``app.user_middleware`` lists middleware outermost first (Starlette inserts each
    ``add_middleware`` call at the front), so a smaller index runs earlier.
    """
    from ayorai_attractor.api.app import app

    names = [m.cls.__name__ for m in app.user_middleware]

    assert "HeavyRouteConcurrencyLimitMiddleware" in names

    auth = names.index("APIKeyAuthMiddleware")
    limiter = names.index("HeavyRouteConcurrencyLimitMiddleware")
    body = names.index("RequestBodyLimitMiddleware")

    # Unauthenticated requests never take a slot; a rejected request is answered
    # before its body is buffered.
    assert auth < limiter < body


# --- Host-wide scope: slots shared by processes through flock ------------------


def _hold_slots_in_child(directory: str, size: int, take: int, ready: Any, done: Any) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    slots = HostSlots(directory, size)
    for _ in range(take):
        assert slots.acquire() is not None
    ready.set()
    done.wait(10)


def test_host_slots_are_shared_between_processes(tmp_path: Any) -> None:
    import multiprocessing

    from ayorai_attractor.api.load_control import HostSlots

    context = multiprocessing.get_context("fork")
    ready, done = context.Event(), context.Event()
    child = context.Process(target=_hold_slots_in_child, args=(str(tmp_path), 2, 2, ready, done))
    child.start()
    try:
        assert ready.wait(10)
        here = HostSlots(str(tmp_path), 2)
        assert here.acquire() is None  # both slots are held by the other process
    finally:
        done.set()
        child.join(10)
    assert here.acquire() is not None  # released when the other process ended


def test_a_crashed_process_does_not_leak_slots(tmp_path: Any) -> None:
    import multiprocessing
    import os

    from ayorai_attractor.api.load_control import HostSlots

    def crash(directory: str) -> None:
        slots = HostSlots(directory, 2)
        slots.acquire()
        slots.acquire()
        os._exit(1)  # no release, no cleanup

    child = multiprocessing.get_context("fork").Process(target=crash, args=(str(tmp_path),))
    child.start()
    child.join(10)
    assert child.exitcode == 1
    here = HostSlots(str(tmp_path), 2)
    assert {here.acquire(), here.acquire()} == {0, 1}


def test_a_process_does_not_reuse_a_slot_it_holds(tmp_path: Any) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    slots = HostSlots(str(tmp_path), 2)
    first, second = slots.acquire(), slots.acquire()
    assert {first, second} == {0, 1}
    assert slots.acquire() is None
    assert first is not None
    slots.release(first)
    assert slots.acquire() == first


def test_two_workers_share_one_host_limit(tmp_path: Any) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    async def scenario() -> None:
        gate = _Gate()
        # Two middleware instances with their own descriptors behave like two
        # worker processes: flock treats separate open file descriptions apart.
        worker_a = HeavyRouteConcurrencyLimitMiddleware(
            gate, max_inflight=2, host_slots=HostSlots(str(tmp_path), 2)
        )
        worker_b = HeavyRouteConcurrencyLimitMiddleware(
            gate, max_inflight=2, host_slots=HostSlots(str(tmp_path), 2)
        )
        first = asyncio.create_task(_call(worker_a, "/v1/check"))
        second = asyncio.create_task(_call(worker_b, "/v1/check"))
        await asyncio.wait_for(_until(lambda: gate.started >= 2), timeout=5)
        status_a, headers = await _call(worker_a, "/v1/check")
        status_b, _ = await _call(worker_b, "/v1/check")
        assert (status_a, status_b) == (503, 503)
        assert headers[b"retry-after"] == b"1"
        gate.release.set()
        assert (await first)[0] == (await second)[0] == 200
        assert (await _call(worker_b, "/v1/check"))[0] == 200  # slots were released

    asyncio.run(scenario())


def test_host_slot_is_released_when_the_handler_raises(tmp_path: Any) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    async def scenario() -> None:
        gate = _Gate(fail=True)
        gate.release.set()
        slots = HostSlots(str(tmp_path), 1)
        app = HeavyRouteConcurrencyLimitMiddleware(gate, max_inflight=1, host_slots=slots)
        with pytest.raises(RuntimeError):
            await _call(app, "/v1/check")
        assert slots.held == set()
        assert slots.acquire() == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("value", ["global", "cluster", ""])
def test_invalid_scope_is_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    from ayorai_attractor.api.load_control import inflight_scope_from_env

    monkeypatch.setenv("ATTRACTOR_INFLIGHT_SCOPE", value)
    with pytest.raises(ValueError, match="ATTRACTOR_INFLIGHT_SCOPE"):
        inflight_scope_from_env()


def test_host_scope_is_built_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("ATTRACTOR_INFLIGHT_SCOPE", "host")
    monkeypatch.setenv("ATTRACTOR_INFLIGHT_LOCK_DIR", str(tmp_path / "slots"))
    app = HeavyRouteConcurrencyLimitMiddleware(_Gate(), max_inflight=3)
    assert app.host_slots is not None
    assert sorted(p.name for p in (tmp_path / "slots").iterdir()) == [
        "slot-0",
        "slot-1",
        "slot-2",
    ]
    assert oct((tmp_path / "slots").stat().st_mode & 0o777) == "0o700"


@pytest.mark.parametrize("extra_bits", [0o020, 0o002, 0o022])
def test_a_writable_shared_lock_dir_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, extra_bits: int
) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    # Simulated through lstat so the test never creates a world-writable directory;
    # such a directory would let another local user pre-create and hold the slots.
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o700)
    real_lstat = Path.lstat

    def fake_lstat(self: Path) -> Any:
        info = real_lstat(self)
        if self != shared:
            return info
        fields = list(info)
        fields[0] = info.st_mode | extra_bits
        return os.stat_result(fields)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ValueError, match="writable"):
        HostSlots(str(shared), 2)


def test_a_symlinked_slot_is_not_followed(tmp_path: Any) -> None:
    import os

    from ayorai_attractor.api.load_control import HostSlots

    target = tmp_path / "elsewhere"
    target.write_text("keep")
    lock_dir = tmp_path / "slots"
    lock_dir.mkdir(mode=0o700)
    os.symlink(target, lock_dir / "slot-0")
    with pytest.raises(OSError):
        HostSlots(str(lock_dir), 1)
    assert target.read_text() == "keep"


def test_api_refuses_to_start_with_an_invalid_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from ayorai_attractor.api.app import app

    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_INFLIGHT_SCOPE", "global")
    with pytest.raises(ValueError, match="ATTRACTOR_INFLIGHT_SCOPE"):
        with TestClient(app):
            pass


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX uid")
def test_the_default_lock_dir_is_per_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from ayorai_attractor.api.load_control import default_lock_dir

    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert default_lock_dir() == str(tmp_path / "ayorai-attractor-inflight")
    for unusable in ("", "relative/dir"):
        monkeypatch.setenv("XDG_RUNTIME_DIR", unusable)
        fallback = default_lock_dir()
        assert fallback.endswith(f"ayorai-attractor-inflight-{os.getuid()}")
        assert os.path.isabs(fallback)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX advisory locks")
def test_a_lock_dir_owned_by_someone_else_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    from ayorai_attractor.api.load_control import HostSlots

    lock_dir = tmp_path / "slots"
    lock_dir.mkdir(mode=0o700)
    real_lstat = Path.lstat

    class _Foreign:
        def __init__(self, info: os.stat_result) -> None:
            self._info = info

        def __getattr__(self, name: str) -> Any:
            if name == "st_uid":
                return os.getuid() + 1
            return getattr(self._info, name)

    def fake_lstat(self: Path) -> Any:
        info = real_lstat(self)
        return _Foreign(info) if self == lock_dir else info

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ValueError, match="owned by this user"):
        HostSlots(str(lock_dir), 1)
