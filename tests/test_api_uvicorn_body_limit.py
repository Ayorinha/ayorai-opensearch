"""Exercise the request-body size limit against a real Uvicorn server."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _wait_for_server(process: subprocess.Popen[bytes], url: str) -> None:
    for _ in range(200):
        if process.poll() is not None:
            raise AssertionError(
                f"Uvicorn exited before becoming ready (code {process.returncode})"
            )
        try:
            with urllib.request.urlopen(url, timeout=0.25) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.05)
    raise AssertionError("Uvicorn did not become ready within 10 seconds")


def _post_with_content_length(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        data=b"123456789",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _post_chunked_without_content_length(port: int) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(
            "POST",
            "/v1/verify",
            body=iter([b"1234", b"56789"]),
            headers={
                "Content-Type": "application/json",
                "Transfer-Encoding": "chunked",
            },
            encode_chunked=True,
        )
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_request_body_limit_rejects_oversized_bodies_on_real_uvicorn(
    tmp_path: Path,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]

    env = os.environ.copy()
    env["ATTRACTOR_MAX_BODY_BYTES"] = "8"
    env["ATTRACTOR_AUDIT_DB"] = str(tmp_path / "audit.sqlite3")
    env["ATTRACTOR_AUTH_MODE"] = "off"
    env.pop("ATTRACTOR_API_KEYS_SHA256", None)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ayorai_attractor.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(process, f"{base_url}/health")

        length_status, length_body = _post_with_content_length(f"{base_url}/v1/verify")
        assert length_status == 413
        assert json.loads(length_body) == {
            "detail": "Request body exceeds the configured size limit"
        }

        chunked_status, chunked_body = _post_chunked_without_content_length(port)
        assert chunked_status == 413
        assert json.loads(chunked_body) == {
            "detail": "Request body exceeds the configured size limit"
        }
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
