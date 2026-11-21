"""Run the upstream Tessera POSIX one-shot personality against public vectors."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

TESSERA_VERSION = "v1.0.4"
LOG_ORIGIN = "example.com/log/ayorai-adr010-poc"
ED25519_PRIVATE_DER_PREFIX = bytes.fromhex("302e020100300506032b657004220420")
ED25519_PUBLIC_DER_PREFIX = bytes.fromhex("302a300506032b6570032100")


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


def generate_ephemeral_note_keys(work: Path) -> tuple[str, str]:
    """Generate a disposable Ed25519 signed-note key pair using OpenSSL."""
    openssl = shutil.which("openssl")
    if openssl is None:
        raise SystemExit("OpenSSL 3+ is required to generate a disposable test key")

    seed = secrets.token_bytes(32)
    private_der = work / "ephemeral-ed25519-private.der"
    public_der = work / "ephemeral-ed25519-public.der"
    private_der.write_bytes(ED25519_PRIVATE_DER_PREFIX + seed)
    try:
        run(
            [
                openssl,
                "pkey",
                "-inform",
                "DER",
                "-in",
                str(private_der),
                "-pubout",
                "-outform",
                "DER",
                "-out",
                str(public_der),
            ],
            os.environ.copy(),
        )
    finally:
        private_der.unlink(missing_ok=True)

    encoded_public = public_der.read_bytes()
    if (
        len(encoded_public) != len(ED25519_PUBLIC_DER_PREFIX) + 32
        or not encoded_public.startswith(ED25519_PUBLIC_DER_PREFIX)
    ):
        raise RuntimeError("OpenSSL returned an unexpected Ed25519 public-key encoding")

    public_note_key = b"\x01" + encoded_public[-32:]
    key_hash = hashlib.sha256(LOG_ORIGIN.encode("utf-8") + b"\n" + public_note_key)
    key_id = key_hash.digest()[:4].hex()
    private_note_key = b"\x01" + seed

    signer = (
        f"PRIVATE+KEY+{LOG_ORIGIN}+{key_id}+"
        f"{base64.b64encode(private_note_key).decode('ascii')}"
    )
    verifier = (
        f"{LOG_ORIGIN}+{key_id}+"
        f"{base64.b64encode(public_note_key).decode('ascii')}"
    )
    return signer, verifier


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

    with tempfile.TemporaryDirectory(prefix="ayorai-adr010-tessera-") as temporary:
        work = Path(temporary)
        signer, verifier = generate_ephemeral_note_keys(work)
        environment = os.environ.copy()
        environment["LOG_PRIVATE_KEY"] = signer

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
        if origin != LOG_ORIGIN:
            raise RuntimeError(f"unexpected checkpoint origin: {origin}")

        public_key_path = work / "tessera-test.pub"
        public_key_path.write_text(verifier + "\n", encoding="utf-8")
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
