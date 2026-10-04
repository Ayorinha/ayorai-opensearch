import json
import re
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = ("source", "license", "license_status", "sha256", "provenance_url")


def check_manifest(data: dict) -> list[str]:
    errors: list[str] = []
    entries = data.get("entries", [])
    for index, entry in enumerate(entries):
        for field in REQUIRED:
            if field not in entry:
                errors.append(f"entry {index}: missing field {field}")
        if entry.get("license_status") != "COMMERCIAL_DEFAULT":
            errors.append(f"entry {index}: license_status must be COMMERCIAL_DEFAULT")
        sha256 = entry.get("sha256")
        if not isinstance(sha256, str) or not HEX64.fullmatch(sha256):
            errors.append(f"entry {index}: sha256 must be 64 lowercase hexadecimal characters")
        source = entry.get("source")
        if isinstance(source, str) and source.startswith("evals/"):
            errors.append(f"entry {index}: source must not start with evals/")
    return errors


if __name__ == "__main__":
    manifest = Path("configs/training-data-manifest.json")
    errors = check_manifest(json.loads(manifest.read_text(encoding="utf-8")))
    for error in errors:
        print(error)
    sys.exit(1 if errors else 0)
