"""Exercise the upstream Tessera POSIX HTTP conformance personality."""

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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from run_tessera_poc import (
    TESSERA_VERSION,
    generate_ephemeral_note_keys,
    run,
)


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

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"

        server_log_path = work / "server.log"
        server_log = server_log_path.open("w+b")
        process = subprocess.Popen(
            [
                go,
                "run",
                f"github.com/transparency-dev/tessera/cmd/conformance/posix@{TESSERA_VERSION}",
                f"--storage_dir={storage}",
                f"--listen=127.0.0.1:{port}",
            ],
            env=environment,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        try:
            ready = False
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError("Tessera HTTP server exited before becoming ready")
                try:
                    with urlopen(f"{base_url}/checkpoint", timeout=0.5):
                        ready = True
                        break
                except HTTPError as error:
                    if error.code == 404:
                        ready = True
                        break
                    raise
                except URLError:
                    time.sleep(0.25)
            if not ready:
                raise TimeoutError("Tessera HTTP server did not become ready")

            assigned_indices: list[int] = []
            for expected_index, leaf in enumerate(leaves):
                request = Request(
                    f"{base_url}/add",
                    data=leaf,
                    headers={"Content-Type": "application/octet-stream"},
                    method="POST",
                )
                with urlopen(request, timeout=15) as response:
                    assigned_index = int(response.read().decode("ascii").strip())
                if assigned_index != expected_index:
                    raise RuntimeError(
                        f"expected Tessera index {expected_index}, got {assigned_index}"
                    )
                assigned_indices.append(assigned_index)

            if assigned_indices != list(range(len(leaves))):
                raise RuntimeError("Tessera HTTP writer returned non-contiguous indices")

            deadline = time.monotonic() + 30
            checkpoint_lines: list[str] = []
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Tessera HTTP server exited before checkpoint publication")
                try:
                    with urlopen(f"{base_url}/checkpoint", timeout=2) as response:
                        checkpoint_lines = response.read().decode("utf-8").splitlines()
                    if len(checkpoint_lines) >= 3 and int(checkpoint_lines[1]) >= len(leaves):
                        break
                except HTTPError as error:
                    if error.code != 404:
                        raise
                time.sleep(0.25)
            if len(checkpoint_lines) < 3 or int(checkpoint_lines[1]) != len(leaves):
                raise TimeoutError("Tessera did not publish the expected HTTP checkpoint")

            origin = checkpoint_lines[0]
            initial_tree_size = int(checkpoint_lines[1])
            initial_root_hash = base64.b64decode(checkpoint_lines[2], validate=True)
            if origin != "example.com/log/ayorai-adr010-poc":
                raise RuntimeError(f"unexpected HTTP checkpoint origin: {origin}")
            if initial_tree_size != len(leaves) or initial_root_hash != expected_root:
                raise RuntimeError("Tessera HTTP checkpoint root differs from public vector")

            duplicate_request = Request(
                f"{base_url}/add",
                data=leaves[0],
                headers={"Content-Type": "application/octet-stream"},
                method="POST",
            )
            with urlopen(duplicate_request, timeout=15) as response:
                duplicate_index = int(response.read().decode("ascii").strip())
            if duplicate_index != len(leaves):
                raise RuntimeError(
                    "unexpected duplicate behavior from the pinned conformance server: "
                    f"expected new index {len(leaves)}, got {duplicate_index}"
                )

            deadline = time.monotonic() + 30
            final_checkpoint_lines: list[str] = []
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Tessera HTTP server exited before duplicate publication")
                try:
                    with urlopen(f"{base_url}/checkpoint", timeout=2) as response:
                        final_checkpoint_lines = response.read().decode("utf-8").splitlines()
                    if (
                        len(final_checkpoint_lines) >= 3
                        and int(final_checkpoint_lines[1]) >= len(leaves) + 1
                    ):
                        break
                except HTTPError as error:
                    if error.code != 404:
                        raise
                time.sleep(0.25)
            if (
                len(final_checkpoint_lines) < 3
                or int(final_checkpoint_lines[1]) != len(leaves) + 1
            ):
                raise TimeoutError("Tessera did not publish the duplicate HTTP append")

            final_tree_size = int(final_checkpoint_lines[1])
            final_root_hash = base64.b64decode(final_checkpoint_lines[2], validate=True)
            if final_root_hash == initial_root_hash:
                raise RuntimeError("duplicate append unexpectedly left the checkpoint root unchanged")
        finally:
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
        print(f"HTTP_INITIAL_CHECKPOINT_TREE_SIZE={initial_tree_size}")
        print(f"HTTP_INITIAL_CHECKPOINT_ROOT_SHA256={initial_root_hash.hex()}")
        print(f"HTTP_DUPLICATE_APPEND_INDEX={duplicate_index}")
        print("HTTP_DUPLICATE_WAS_DEDUPLICATED=false")
        print(f"HTTP_FINAL_CHECKPOINT_TREE_SIZE={final_tree_size}")
        print(f"HTTP_FINAL_CHECKPOINT_ROOT_SHA256={final_root_hash.hex()}")
        print("HTTP_CHECKPOINT_SIGNATURE=VERIFIED_BY_TESSERA_FSCK")
        print("HTTP_TILE_AND_ENTRY_BUNDLE_INTEGRITY=VERIFIED_BY_TESSERA_FSCK")


if __name__ == "__main__":
    main()
