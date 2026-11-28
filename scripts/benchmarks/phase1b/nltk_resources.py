#!/usr/bin/env python3
"""Pinned, hash-verified NLTK punkt_tab resource for the official MiniCheck/FactCG chunking.

Install happens once, in a controlled workflow step. At inference time the resource is only
verified and loaded from a private directory; network downloads are blocked.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

NLTK_PIN_PATH = Path("configs/benchmarks/nltk-punkt-tab-pin.json")


def load_pin(path: Path = NLTK_PIN_PATH) -> dict[str, Any]:
    pin = json.loads(path.read_text(encoding="utf-8"))
    for key in ("nltk_version", "source_url", "zip_sha256", "zip_size_bytes", "files"):
        if key not in pin:
            raise ValueError("NLTK pin is incomplete")
    if pin["nltk_data_commit"] not in pin["source_url"]:
        raise ValueError("NLTK source URL is not pinned to the declared commit")
    return pin


def install_from_zip_bytes(payload: bytes, pin: dict[str, Any], data_dir: Path) -> None:
    """Verify the archive and extract ONLY the pinned files into ``data_dir/tokenizers``."""
    if len(payload) != pin["zip_size_bytes"]:
        raise ValueError("punkt_tab archive size mismatch")
    if hashlib.sha256(payload).hexdigest() != pin["zip_sha256"]:
        raise ValueError("punkt_tab archive SHA-256 mismatch")
    target_root = data_dir / "tokenizers"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name, expected in pin["files"].items():
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != expected["sha256"]:
                raise ValueError("punkt_tab member SHA-256 mismatch")
            destination = (target_root / name).resolve()
            if target_root.resolve() not in destination.parents:
                raise ValueError("unsafe archive member path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    verify_files(pin, data_dir)


def verify_files(pin: dict[str, Any], data_dir: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for name, expected in pin["files"].items():
        path = data_dir / "tokenizers" / name
        if not path.is_file():
            raise ValueError("pinned punkt_tab file is missing")
        content = path.read_bytes()
        if len(content) != expected["size_bytes"]:
            raise ValueError("punkt_tab file size mismatch")
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected["sha256"]:
            raise ValueError("punkt_tab file SHA-256 mismatch")
        verified[name] = digest
    return verified


def _vendored() -> Any:
    try:
        from . import vendor_nltk
    except ImportError:  # direct script execution
        import vendor_nltk  # type: ignore[no-redef]
    return vendor_nltk


def prepare_runtime(pin: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    """Verify version and files and point the vendored segmentation at ``data_dir``.

    The shards use the nltk 3.9.4 segmentation vendored in ``vendor_nltk`` (P4-01):
    nltk itself is not installed, so nothing can download or load other resources.
    """
    vendor_nltk = _vendored()
    if vendor_nltk.NLTK_VERSION != pin["nltk_version"]:
        raise RuntimeError("vendored nltk version does not match the pin")
    verified = verify_files(pin, data_dir)
    vendor_nltk.configure(data_dir)
    return {
        "nltk_version": vendor_nltk.NLTK_VERSION,
        "nltk_data_commit": pin["nltk_data_commit"],
        "punkt_tab_zip_sha256": pin["zip_sha256"],
        "punkt_tab_files_sha256": verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, default=NLTK_PIN_PATH)
    parser.add_argument("--data-dir", required=True, type=Path)
    args = parser.parse_args()
    pin = load_pin(args.pin)
    from urllib.request import urlopen

    with urlopen(pin["source_url"], timeout=120) as response:  # nosec B310 - pinned https URL
        payload = response.read()
    install_from_zip_bytes(payload, pin, args.data_dir)
    print(json.dumps({"status": "punkt_tab_installed_and_verified", "files": len(pin["files"])}))


if __name__ == "__main__":
    main()
