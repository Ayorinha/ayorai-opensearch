"""Run the upstream Tessera POSIX one-shot personality against public vectors.

This downloads and runs the pinned upstream Tessera v1.0.4 examples. It uses
the publicly documented upstream demo key, which is intentionally public and
must never be used for a real log.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

TESSERA_VERSION = "v1.0.4"
TEST_PRIVATE_KEY = (
    "PRIVATE+KEY+example.com/log/testdata+33d7b496+"
    "AeymY/SZAX0jZcJ8enZ5FY1Dz+wTML2yWSkK+9DSF3eg"
)
TEST_PUBLIC_KEY = (
    "example.com/log/testdata+33d7b496+"
    "AeHTu4Q3hEIMHNqc6fASMsq3rKNx280NI+oO5xCFkkSx"
)


def run(command: list[str], env: dict[str, str], timeout: int = 300) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed with exit code {result.returncode}: "
            f"{' '.join(command)}\n{output}"
        )
    return output


def main() -> None:
    go = shutil.which("go")
    if go is None:
        raise SystemExit("Go 1.24+ is required for the Tessera proof of concept")

    root = Path(__file__).resolve().parents[2]
    vector_path = root / "tests" / "auditlog" / "vectors" / "rfc6962-transparency-dev.json"
    vectors = json.loads(vector_path.read_text(encoding="utf-8"))
    leaves = [bytes.fromhex(value) for value in vectors["leaves_hex"]]
    expected_root = bytes.fromhex(vectors["roots"][len(leaves)])

    if len(leaves) != 17:
        raise SystemExit(f"expected the existing 17 public reference leaves, got {len(leaves)}")

    environment = os.environ.copy()
    environment["LOG_PRIVATE_KEY"] = TEST_PRIVATE_KEY

    with tempfile.TemporaryDirectory(prefix="ayorai-adr010-tessera-") as temporary:
        work = Path(temporary)
        storage = work / "log"
        entries = work / "entries"
        entries.mkdir()
        for index, leaf in enumerate(leaves):
            (entries / f"{index:03d}.entry").write_bytes(leaf)

        append_output = run(
            [
                go,
                "run",
                f"github.com/transparency-dev/tessera/cmd/examples/posix-oneshot@{TESSERA_VERSION}",
                f"--storage_dir={storage}",
                f"--entries={entries}/*",
            ],
            environment,
        )
        if "Failed" in append_output or "ERROR" in append_output:
            raise RuntimeError(f"Tessera append reported an error:\n{append_output}")

        checkpoint_path = storage / "checkpoint"
        if not checkpoint_path.is_file():
            raise RuntimeError("Tessera did not publish a checkpoint")
        checkpoint_lines = checkpoint_path.read_text(encoding="utf-8").splitlines()
        if len(checkpoint_lines) < 3:
            raise RuntimeError("Tessera checkpoint has fewer than three required lines")

        origin = checkpoint_lines[0]
        tree_size = int(checkpoint_lines[1])
        root_hash = base64.b64decode(checkpoint_lines[2], validate=True)
        if tree_size != len(leaves):
            raise RuntimeError(f"expected checkpoint size {len(leaves)}, got {tree_size}")
        if root_hash != expected_root:
            raise RuntimeError(
                "Tessera root differs from the existing independent Go reference vector"
            )
        if origin != "example.com/log/testdata":
            raise RuntimeError(f"unexpected checkpoint origin: {origin}")

        public_key_path = work / "tessera-test.pub"
        public_key_path.write_text(TEST_PUBLIC_KEY + "\n", encoding="utf-8")
        fsck_output = run(
            [
                go,
                "run",
                f"github.com/transparency-dev/tessera/cmd/fsck@{TESSERA_VERSION}",
                f"--storage_url={storage.as_uri()}/",
                f"--public_key={public_key_path}",
                "--ui=false",
            ],
            environment,
        )
        if "fsck failed:" in fsck_output.lower():
            raise RuntimeError(f"Tessera fsck rejected the log:\n{fsck_output}")

        print(f"TESSERA_VERSION={TESSERA_VERSION}")
        print(f"VECTOR_LEAVES={len(leaves)}")
        print(f"CHECKPOINT_ORIGIN={origin}")
        print(f"CHECKPOINT_TREE_SIZE={tree_size}")
        print(f"CHECKPOINT_ROOT_SHA256={root_hash.hex()}")
        print("CHECKPOINT_SIGNATURE=VERIFIED_BY_TESSERA_FSCK")
        print("TILE_AND_ENTRY_BUNDLE_INTEGRITY=VERIFIED_BY_TESSERA_FSCK")


if __name__ == "__main__":
    main()
