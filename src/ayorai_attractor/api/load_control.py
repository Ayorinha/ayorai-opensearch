"""Admission control for CPU-bound routes.

The verification routes run synchronous, CPU-bound work in the worker's thread
pool. Without a bound, every accepted request queues behind the others: in the
2026-11-15 load test (one worker, 16 clients sending 2 MB /v1/check bodies) the
median latency reached 31 s and resident memory 1.6 GiB, because every request
held its parsed documents while waiting. Rejecting work beyond a small number of
in-flight requests keeps latency and memory bounded and tells clients when to
retry (HTTP 503 with ``Retry-After``).

By default the limit is per worker process: N workers admit N times the limit.
With ``ATTRACTOR_INFLIGHT_SCOPE=host`` the workers of one host share the limit
through advisory locks on ``max_inflight`` slot files in
``ATTRACTOR_INFLIGHT_LOCK_DIR``; the kernel releases a slot when the process
holding it exits, so a crashed worker cannot leak capacity. Replicas on other
hosts still need a limit at the gateway.
The in-process counter and slot set are only touched on the event loop, with no
``await`` between the check and the update, so no in-process lock is needed.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

DEFAULT_MAX_INFLIGHT = 2
HEAVY_PATHS = frozenset({"/v1/check", "/v1/fields", "/v1/verify", "/v1/audit", "/v1/opensearch"})
RETRY_AFTER_SECONDS = 1
SCOPES = ("process", "host")
LOCK_DIR_NAME = "ayorai-attractor-inflight"


def default_lock_dir() -> str:
    """Per-user slot directory: $XDG_RUNTIME_DIR, else the temp dir with the uid.

    A fixed name in a world-writable directory would let another local user
    create it first and hold the slots; the uid suffix keeps users apart, and
    HostSlots still refuses a directory this user does not own.
    """
    runtime = os.getenv("XDG_RUNTIME_DIR", "").strip()
    if runtime and Path(runtime).is_absolute():
        return str(Path(runtime) / LOCK_DIR_NAME)
    return str(Path(tempfile.gettempdir()) / f"{LOCK_DIR_NAME}-{os.getuid()}")


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


def inflight_scope_from_env() -> str:
    """Read ATTRACTOR_INFLIGHT_SCOPE: "process" (default) or "host"."""
    scope = os.getenv("ATTRACTOR_INFLIGHT_SCOPE", "process").strip().lower()
    if scope not in SCOPES:
        raise ValueError("ATTRACTOR_INFLIGHT_SCOPE must be 'process' or 'host'")
    if scope == "host" and sys.platform == "win32":
        raise ValueError("ATTRACTOR_INFLIGHT_SCOPE=host requires POSIX advisory locks")
    return scope


class HostSlots:
    """``size`` slots shared by the processes of one host via ``fcntl.flock``.

    A slot is an exclusive, non-blocking lock on one file. ``flock`` locks belong
    to the open file description, so a process does not exclude itself; slots it
    already holds are tracked in ``held`` and never tried again until released.
    """

    def __init__(self, directory: str, size: int) -> None:
        import fcntl

        self._fcntl = fcntl
        path = Path(directory)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("ATTRACTOR_INFLIGHT_LOCK_DIR must be a directory owned by this user")
        if info.st_mode & 0o022:
            raise ValueError("ATTRACTOR_INFLIGHT_LOCK_DIR must not be group or world writable")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self._fds = [os.open(path / f"slot-{index}", flags, 0o600) for index in range(size)]
        self.held: set[int] = set()

    def acquire(self) -> int | None:
        for index, fd in enumerate(self._fds):
            if index in self.held:
                continue
            try:
                self._fcntl.flock(fd, self._fcntl.LOCK_EX | self._fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            self.held.add(index)
            return index
        return None

    def release(self, index: int) -> None:
        self.held.discard(index)
        self._fcntl.flock(self._fds[index], self._fcntl.LOCK_UN)


class HeavyRouteConcurrencyLimitMiddleware:
    """Reject heavy requests beyond a per-process in-flight limit with 503."""

    def __init__(
        self,
        app: ASGIApp,
        max_inflight: int | None = None,
        *,
        host_slots: HostSlots | None = None,
    ) -> None:
        self.app = app
        self.max_inflight = max_inflight if max_inflight is not None else max_inflight_from_env()
        if self.max_inflight <= 0:
            raise ValueError("max_inflight must be a positive integer")
        if host_slots is None and inflight_scope_from_env() == "host":
            lock_dir = os.getenv("ATTRACTOR_INFLIGHT_LOCK_DIR") or default_lock_dir()
            host_slots = HostSlots(lock_dir, self.max_inflight)
        self.host_slots = host_slots
        self.inflight = 0
        self.rejected = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in HEAVY_PATHS:
            await self.app(scope, receive, send)
            return
        slots = self.host_slots
        slot: int | None = None
        if self.inflight < self.max_inflight and slots is not None:
            slot = slots.acquire()
        if self.inflight >= self.max_inflight or (slots is not None and slot is None):
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
            if slots is not None and slot is not None:
                slots.release(slot)
