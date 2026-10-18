"""The structured access record must reach the server output under real Uvicorn."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from ayorai_attractor.api.logging_config import configure_logging, resolve_log_level


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        return int(reserved.getsockname()[1])


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("ATTRACTOR_LOG_LEVEL", None)
    env["ATTRACTOR_AUTH_MODE"] = "off"
    env["ATTRACTOR_AUDIT_DB"] = str(tmp_path / "audit.sqlite3")
    env.update(extra)
    return env


def _uvicorn(port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "ayorai_attractor.api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--lifespan",
        "on",
        "--no-access-log",
    ]


def _access_events(output: str) -> list[dict[str, object]]:
    events = []
    for line in output.splitlines():
        if line.startswith("{") and '"request_id"' in line:
            events.append(json.loads(line))
    return events


def test_access_record_is_emitted_by_real_uvicorn(tmp_path: Path) -> None:
    port = _free_port()
    process = subprocess.Popen(
        _uvicorn(port),
        env=_env(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(200):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health?secret=never-logged", timeout=0.25
                ) as response:
                    assert response.status == 200
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.05)
        else:
            raise AssertionError("Uvicorn did not become ready within 10 seconds")
    finally:
        process.terminate()
        output, _ = process.communicate(timeout=10)

    text = output.decode()
    events = _access_events(text)
    assert events, text
    assert events[-1]["route"] == "/health"
    assert events[-1]["status"] == 200
    assert "never-logged" not in text


def test_invalid_log_level_stops_startup(tmp_path: Path) -> None:
    completed = subprocess.run(
        _uvicorn(_free_port()),
        env=_env(tmp_path, ATTRACTOR_LOG_LEVEL="LOUD"),
        capture_output=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout.decode() + completed.stderr.decode()
    assert completed.returncode != 0
    assert "ATTRACTOR_LOG_LEVEL must be one of" in output


def test_configure_logging_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = logging.getLogger("ayorai_attractor")
    before = list(logger.handlers)
    previous_level = logger.level
    monkeypatch.setenv("ATTRACTOR_LOG_LEVEL", "warning")
    try:
        configure_logging()
        configure_logging()
        added = [handler for handler in logger.handlers if handler not in before]
        assert len([h for h in added if getattr(h, "_ayorai_attractor_handler", False)]) <= 1
        assert logger.level == logging.WARNING
        assert resolve_log_level() == logging.WARNING
    finally:
        for handler in list(logger.handlers):
            if handler not in before:
                logger.removeHandler(handler)
        logger.setLevel(previous_level)
