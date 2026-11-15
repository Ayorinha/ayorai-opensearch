"""The Docker image installs only hash-locked dependencies that satisfy pyproject.toml."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docker" / "requirements.lock"
ENTRY = re.compile(r"^([A-Za-z0-9._-]+)==(\S+) \\\n    --hash=sha256:([0-9a-f]{64})$", re.MULTILINE)


def _locked() -> dict[str, Version]:
    text = LOCK.read_text(encoding="utf-8")
    entries = ENTRY.findall(text)
    body = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert len(body) == 2 * len(entries), "every locked line must be name==version + one sha256"
    return {canonicalize_name(name): Version(version) for name, version, _ in entries}


def test_every_runtime_dependency_is_locked_within_its_range() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    locked = _locked()
    for spec in project["dependencies"]:
        requirement = Requirement(spec)
        name = canonicalize_name(requirement.name)
        assert name in locked, f"{name} is not in docker/requirements.lock"
        assert requirement.specifier.contains(locked[name], prereleases=True), (
            f"{name}=={locked[name]} does not satisfy {requirement.specifier}"
        )


def test_build_tools_are_locked_and_the_dockerfile_requires_hashes() -> None:
    locked = _locked()
    assert {"setuptools", "wheel"} <= set(locked)
    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert "--require-hashes --only-binary=:all: -r docker/requirements.lock" in dockerfile
    assert "pip install --no-cache-dir --no-deps --no-build-isolation ." in dockerfile
    assert "pip uninstall --yes setuptools wheel packaging" in dockerfile
