#!/usr/bin/env python3
"""Download the pinned LLM-AggreFact DEV shard and verify size + SHA-256 before use.

Prints no dataset content. Fails closed on any mismatch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from .common import DEV_PIN_PATH, sha256_file
except ImportError:  # direct script execution
    from common import DEV_PIN_PATH, sha256_file

EXPECTED_FILE = "data/dev-00000-of-00001.parquet"


def validate_pin(pin: dict[str, Any]) -> None:
    if pin.get("file") != EXPECTED_FILE:
        raise SystemExit("DEV shard integrity check failed")
    if not re.fullmatch(r"[a-f0-9]{40}", str(pin.get("revision", ""))):
        raise SystemExit("DEV shard integrity check failed")
    if not re.fullmatch(r"[a-f0-9]{64}", str(pin.get("sha256", ""))):
        raise SystemExit("DEV shard integrity check failed")


def verify_file(path: Path, pin: dict[str, Any]) -> None:
    if path.stat().st_size != pin["size_bytes"] or sha256_file(path) != pin["sha256"]:
        raise SystemExit("DEV shard integrity check failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, default=DEV_PIN_PATH)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    validate_pin(pin)
    from huggingface_hub import hf_hub_download

    downloaded = Path(
        hf_hub_download(
            repo_id=pin["dataset"],
            repo_type="dataset",
            filename=pin["file"],
            revision=pin["revision"],
            token=os.environ.get("HF_TOKEN") or None,
        )
    )
    verify_file(downloaded, pin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(downloaded, args.output)
    verify_file(args.output, pin)
    print(json.dumps({"status": "dev_shard_verified", "split": "dev"}))


if __name__ == "__main__":
    main()
