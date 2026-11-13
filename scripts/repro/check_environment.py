"""Compare the running Python environment with a historical reproduction manifest.

Usage: python scripts/repro/check_environment.py MANIFEST.json {inference|aggregate|aggregate-minimal}
Exits 0 only when Python X.Y.Z and every recorded package version match exactly.
"""

from __future__ import annotations

import json
import platform
import sys
from collections.abc import Callable, Mapping
from importlib import metadata
from pathlib import Path


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def compare(
    manifest: Mapping[str, object],
    environment: str,
    *,
    python_version: str,
    installed: Callable[[str], str | None],
) -> list[str]:
    """Return human-readable mismatches; an empty list means an exact match."""
    runtime = manifest["runtime"]
    environments = manifest["environments"]
    if not isinstance(runtime, Mapping) or not isinstance(environments, Mapping):
        raise ValueError("manifest is missing runtime/environments")
    if environment not in environments:
        raise ValueError(f"unknown environment {environment!r}")
    spec = environments[environment]
    if not isinstance(spec, Mapping):
        raise ValueError("environment spec must be an object")
    problems: list[str] = []
    if python_version != runtime["python"]:
        problems.append(f"python: expected {runtime['python']}, found {python_version}")
    packages = spec["packages"]
    if not isinstance(packages, Mapping):
        raise ValueError("packages must be an object")
    for name, expected in sorted(packages.items(), key=lambda item: _normalize(item[0])):
        found = installed(name)
        if found != expected:
            problems.append(f"{_normalize(name)}: expected {expected}, found {found or 'missing'}")
    forbidden = spec.get("forbidden_packages", [])
    if not isinstance(forbidden, list):
        raise ValueError("forbidden_packages must be a list")
    for name in sorted(forbidden, key=_normalize):
        found = installed(name)
        if found is not None:
            problems.append(f"{_normalize(name)}: unexpected package {found}")
    return problems


def _installed(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    manifest = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    problems = compare(
        manifest, argv[1], python_version=platform.python_version(), installed=_installed
    )
    for problem in problems:
        print(f"MISMATCH {problem}")
    print("REPRO_ENVIRONMENT: " + ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
