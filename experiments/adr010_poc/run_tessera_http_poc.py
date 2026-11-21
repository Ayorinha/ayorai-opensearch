"""Exercise Tessera's POSIX HTTP personality and its antispam limits."""

from __future__ import annotations

import base64
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from run_tessera_poc import (
    TESSERA_VERSION,
    generate_ephemeral_note_keys,
    run,
)


def start_server(
    go: str,
    storage: Path,
    environment: dict[str, str],
    work: Path,
    label: str,
    persistent_antispam: bool = False,
) -> tuple[subprocess.Popen[bytes], BinaryIO, str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    server_log = (work / f"{label}.log").open("w+b")
    command = [
        go,
        "run",
        f"github.com/transparency-dev/tessera/cmd/conformance/posix@{TESSERA_VERSION}",
        f"--storage_dir={storage}",
        f"--listen=127.0.0.1:{port}",
    ]
    if persistent_antispam:
        command.append("--antispam=true")
    process = subprocess.Popen(
        command,
        env=environment,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError("Tessera HTTP server exited before becoming ready")
            try:
                with urlopen(f"{base_url}/checkpoint", timeout=0.5):
                    return process, server_log, base_url
            except HTTPError as error:
                if error.code == 404:
                    return process, server_log, base_url
                raise
            except URLError:
                time.sleep(0.25)
        raise TimeoutError("Tessera HTTP server did not become ready")
    except Exception as error:
        server_log.flush()
        server_log.seek(0)
        detail = server_log.read().decode("utf-8", errors="replace")
        stop_server(process, server_log)
        raise RuntimeError(f"HTTP server startup failed:\n{detail}") from error


def stop_server(process: subprocess.Popen[bytes], server_log: BinaryIO) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
    server_log.close()


def post_entry(base_url: str, leaf: bytes, idempotency_key: str) -> int:
    request = Request(
        f"{base_url}/add",
        data=leaf,
        headers={
            "Content-Type": "application/octet-stream",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return int(response.read().decode("ascii").strip())


def wait_for_checkpoint(base_url: str, expected_size: int) -> tuple[str, int, bytes]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/checkpoint", timeout=2) as response:
                lines = response.read().decode("utf-8").splitlines()
            if len(lines) >= 3:
                tree_size = int(lines[1])
                if tree_size >= expected_size:
                    return (
                        lines[0],
                        tree_size,
                        base64.b64decode(lines[2], validate=True),
                    )
        except HTTPError as error:
            if error.code != 404:
                raise
        time.sleep(0.25)
    raise TimeoutError(f"Tessera did not publish checkpoint size {expected_size}")


def main() -> None:
    go = shutil.which("go")
    if go is None:
        raise SystemExit("Go 1.24+ is required for the Tessera HTTP proof of concept")

    root = Path(__file__).resolve().parents[2]
    vector_path = root / "tests" / "auditlog" / "vectors" / "rfc6962-transparency-dev.json"
    vectors = json.loads(vector_path.read_text(encoding="utf-8"))
    leaves = [bytes.fromhex(value) for value in vectors["leaves_hex"][:5]]
    expected_root = bytes.fromhex(vectors["roots"][len(leaves)])

    with tempfile.TemporaryDirectory(prefix="ayorai-adr010-tessera-http-") as temporary:
        work = Path(temporary)
        storage = work / "log"
        storage.mkdir()
        signer, verifier = generate_ephemeral_note_keys(work)
        environment = os.environ.copy()
        environment["LOG_PRIVATE_KEY"] = signer
        public_key_path = work / "tessera-http-test.pub"
        public_key_path.write_text(verifier + "\n", encoding="utf-8")

        first_process, first_log, first_url = start_server(
            go, storage, environment, work, "server-first"
        )
        try:
            assigned_indices = []
            for index, leaf in enumerate(leaves):
                key = "same-idempotency-key" if index == 0 else f"key-{index}"
                assigned_indices.append(post_entry(first_url, leaf, key))
            if assigned_indices != list(range(len(leaves))):
                raise RuntimeError(f"unexpected initial Tessera indices: {assigned_indices}")

            origin, initial_size, initial_root = wait_for_checkpoint(first_url, len(leaves))
            if origin != "example.com/log/ayorai-adr010-poc":
                raise RuntimeError(f"unexpected HTTP checkpoint origin: {origin}")
            if initial_size != len(leaves) or initial_root != expected_root:
                raise RuntimeError("Tessera HTTP checkpoint root differs from public vector")

            immediate_duplicate_index = post_entry(
                first_url, leaves[0], "same-idempotency-key"
            )
            if immediate_duplicate_index != 0:
                raise RuntimeError(
                    "expected in-memory antispam to return original index 0, "
                    f"got {immediate_duplicate_index}"
                )
            _, size_after_immediate_retry, root_after_immediate_retry = wait_for_checkpoint(
                first_url, len(leaves)
            )
            if (
                size_after_immediate_retry != initial_size
                or root_after_immediate_retry != initial_root
            ):
                raise RuntimeError("immediate duplicate unexpectedly changed the Tessera log")
        finally:
            stop_server(first_process, first_log)

        second_process, second_log, second_url = start_server(
            go, storage, environment, work, "server-restarted"
        )
        try:
            restart_duplicate_index = post_entry(
                second_url, leaves[0], "same-idempotency-key"
            )
            if restart_duplicate_index != len(leaves):
                raise RuntimeError(
                    "expected the in-memory antispam cache to reset after restart; "
                    f"expected index {len(leaves)}, got {restart_duplicate_index}"
                )

            same_key_different_body_index = post_entry(
                second_url, leaves[1], "same-idempotency-key"
            )
            if same_key_different_body_index != len(leaves) + 1:
                raise RuntimeError(
                    "expected the conformance endpoint to ignore Idempotency-Key; "
                    f"expected index {len(leaves) + 1}, got {same_key_different_body_index}"
                )

            final_origin, final_size, final_root = wait_for_checkpoint(
                second_url, len(leaves) + 2
            )
            if final_origin != origin or final_size != len(leaves) + 2:
                raise RuntimeError("unexpected checkpoint after Tessera process restart")
            if final_root == initial_root:
                raise RuntimeError("restart retries did not change the Tessera checkpoint")
        finally:
            stop_server(second_process, second_log)

        fsck_output = run(
            [
                go,
                "run",
                f"github.com/transparency-dev/tessera/cmd/fsck@{TESSERA_VERSION}",
                f"--storage_url={storage.as_uri()}/",
                f"--public_key={public_key_path}",
                "--ui=false",
            ],
            os.environ.copy(),
        )
        if "fsck failed:" in fsck_output.lower():
            raise RuntimeError(f"Tessera HTTP log failed fsck:\n{fsck_output}")

        print(f"TESSERA_HTTP_VERSION={TESSERA_VERSION}")
        print(f"HTTP_INITIAL_ENTRIES={len(leaves)}")
        print(f"HTTP_INITIAL_CHECKPOINT_TREE_SIZE={initial_size}")
        print(f"HTTP_INITIAL_CHECKPOINT_ROOT_SHA256={initial_root.hex()}")
        print(f"HTTP_IMMEDIATE_DUPLICATE_INDEX={immediate_duplicate_index}")
        print(f"HTTP_RESTART_DUPLICATE_INDEX={restart_duplicate_index}")
        print(f"HTTP_SAME_KEY_DIFFERENT_BODY_INDEX={same_key_different_body_index}")
        print("HTTP_ANTISPAM_SURVIVES_RESTART=false")
        print("HTTP_IDEMPOTENCY_KEY_CONTRACT_ENFORCED=false")
        print(f"HTTP_FINAL_CHECKPOINT_TREE_SIZE={final_size}")
        print(f"HTTP_FINAL_CHECKPOINT_ROOT_SHA256={final_root.hex()}")
        print("HTTP_CHECKPOINT_SIGNATURE=VERIFIED_BY_TESSERA_FSCK")
        print("HTTP_TILE_AND_ENTRY_BUNDLE_INTEGRITY=VERIFIED_BY_TESSERA_FSCK")

        persistent_storage = work / "persistent-log"
        persistent_storage.mkdir()
        persistent_first, persistent_first_log, persistent_first_url = start_server(
            go, persistent_storage, environment, work, "server-persistent-first", True
        )
        try:
            persistent_indices = []
            for index, leaf in enumerate(leaves):
                key = "same-idempotency-key" if index == 0 else f"key-{index}"
                persistent_indices.append(post_entry(persistent_first_url, leaf, key))
            if persistent_indices != list(range(len(leaves))):
                raise RuntimeError("persistent antispam initial indices are not contiguous")
            persistent_origin, persistent_initial_size, persistent_initial_root = (
                wait_for_checkpoint(persistent_first_url, len(leaves))
            )
            if (
                persistent_origin != origin
                or persistent_initial_size != len(leaves)
                or persistent_initial_root != expected_root
            ):
                raise RuntimeError("persistent antispam initial checkpoint differs from vector")
            persistent_immediate_duplicate = post_entry(
                persistent_first_url, leaves[0], "same-idempotency-key"
            )
            if persistent_immediate_duplicate != 0:
                raise RuntimeError("persistent antispam did not suppress immediate duplicate")
        finally:
            stop_server(persistent_first, persistent_first_log)

        persistent_second, persistent_second_log, persistent_second_url = start_server(
            go, persistent_storage, environment, work, "server-persistent-restarted", True
        )
        try:
            persistent_restart_duplicate = post_entry(
                persistent_second_url, leaves[0], "same-idempotency-key"
            )
            if persistent_restart_duplicate != 0:
                raise RuntimeError(
                    "persistent antispam did not suppress duplicate after restart; "
                    f"got index {persistent_restart_duplicate}"
                )
            persistent_same_key_different_body = post_entry(
                persistent_second_url, leaves[1], "same-idempotency-key"
            )
            if persistent_same_key_different_body != len(leaves):
                raise RuntimeError(
                    "persistent antispam should deduplicate by body, not Idempotency-Key"
                )
            persistent_final_origin, persistent_final_size, persistent_final_root = (
                wait_for_checkpoint(persistent_second_url, len(leaves) + 1)
            )
            if (
                persistent_final_origin != persistent_origin
                or persistent_final_size != len(leaves) + 1
                or persistent_final_root == persistent_initial_root
            ):
                raise RuntimeError("persistent antispam final checkpoint is inconsistent")
        finally:
            stop_server(persistent_second, persistent_second_log)

        persistent_fsck_output = run(
            [
                go,
                "run",
                f"github.com/transparency-dev/tessera/cmd/fsck@{TESSERA_VERSION}",
                f"--storage_url={persistent_storage.as_uri()}/",
                f"--public_key={public_key_path}",
                "--ui=false",
            ],
            os.environ.copy(),
        )
        if "fsck failed:" in persistent_fsck_output.lower():
            raise RuntimeError(
                f"Tessera persistent-antispam log failed fsck:\n{persistent_fsck_output}"
            )

        print("HTTP_PERSISTENT_ANTISPAM_ENABLED=true")
        print(f"HTTP_PERSISTENT_INITIAL_TREE_SIZE={persistent_initial_size}")
        print(f"HTTP_PERSISTENT_IMMEDIATE_DUPLICATE_INDEX={persistent_immediate_duplicate}")
        print(f"HTTP_PERSISTENT_RESTART_DUPLICATE_INDEX={persistent_restart_duplicate}")
        print(
            "HTTP_PERSISTENT_SAME_KEY_DIFFERENT_BODY_INDEX="
            f"{persistent_same_key_different_body}"
        )
        print("HTTP_PERSISTENT_ANTISPAM_SURVIVES_RESTART=true")
        print("HTTP_PERSISTENT_IDEMPOTENCY_KEY_CONTRACT_ENFORCED=false")
        print(f"HTTP_PERSISTENT_FINAL_TREE_SIZE={persistent_final_size}")
        print(f"HTTP_PERSISTENT_FINAL_ROOT_SHA256={persistent_final_root.hex()}")
        print("HTTP_PERSISTENT_FSCK=PASS")


if __name__ == "__main__":
    main()
