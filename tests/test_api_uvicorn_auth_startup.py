"""Fail-closed authentication must stop a real Uvicorn server at startup."""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        return int(reserved.getsockname()[1])


def _env_without_auth(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    for name in list(env):
        if name.startswith("ATTRACTOR_API_KEY") or name == "ATTRACTOR_AUTH_MODE":
            env.pop(name)
    env["ATTRACTOR_AUDIT_DB"] = str(tmp_path / "audit.sqlite3")
    return env


@pytest.mark.parametrize("auth_mode", [None, "api_key"])
def test_uvicorn_refuses_to_start_without_auth_configuration(
    tmp_path: Path, auth_mode: str | None
) -> None:
    env = _env_without_auth(tmp_path)
    if auth_mode is not None:
        env["ATTRACTOR_AUTH_MODE"] = auth_mode

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ayorai_attractor.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(_free_port()),
            "--lifespan",
            "on",
        ],
        env=env,
        capture_output=True,
        timeout=30,
        check=False,
    )

    output = completed.stdout.decode() + completed.stderr.decode()
    assert completed.returncode != 0
    assert "Application startup failed" in output
    assert "Uvicorn running on" not in output


def _cmd_has_lifespan_on(command: str) -> bool:
    return re.search(r"--lifespan[\"',\s=]+on\b", command) is not None


def test_dockerfile_command_forces_lifespan_on() -> None:
    dockerfile = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    commands = [line for line in dockerfile.splitlines() if line.startswith('CMD ["uvicorn"')]
    assert commands, "Dockerfile must start the API with uvicorn"
    assert all(_cmd_has_lifespan_on(line) for line in commands)


def test_makefile_run_target_forces_lifespan_on() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    commands = [line for line in makefile.splitlines() if "uvicorn " in line]
    assert commands, "Makefile must start the API with uvicorn"
    assert all(_cmd_has_lifespan_on(line) for line in commands)
