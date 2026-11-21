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

from experiments.adr010_poc.run_tessera_poc import (
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
            tree_size = int(checkpoint_lines[1])
            root_hash = base64.b64decode(checkpoint_lines[2], validate=True)
            if origin != "example.com/log/ayorai-adr010-poc":
                raise RuntimeError(f"unexpected HTTP checkpoint origin: {origin}")
            if root_hash != expected_root:
                raise RuntimeError("Tessera HTTP checkpoint root differs from public vector")
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
        print(f"HTTP_ENTRIES={len(leaves)}")
        print(f"HTTP_CHECKPOINT_ORIGIN={origin}")
        print(f"HTTP_CHECKPOINT_TREE_SIZE={tree_size}")
        print(f"HTTP_CHECKPOINT_ROOT_SHA256={root_hash.hex()}")
        print("HTTP_CHECKPOINT_SIGNATURE=VERIFIED_BY_TESSERA_FSCK")
        print("HTTP_TILE_AND_ENTRY_BUNDLE_INTEGRITY=VERIFIED_BY_TESSERA_FSCK")


if __name__ == "__main__":
    main()
