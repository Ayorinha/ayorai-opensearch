"""Integrity tests for the historical Phase 1b DEV reproduction record (synthetic checks only)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.repro.check_environment import compare

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reproducibility" / "phase1b-dev-2026-11-07"
MANIFEST = json.loads((RECORD / "MANIFEST.json").read_text(encoding="utf-8"))
_PIN = re.compile(r"^([A-Za-z0-9_.-]+)==(\S+) \\$", re.M)


def _pins(path: Path) -> dict[str, str]:
    return dict(_PIN.findall(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("environment", ["inference", "aggregate", "aggregate-minimal", "plan"])
def test_lock_file_matches_manifest_and_requires_hashes(environment: str) -> None:
    spec = MANIFEST["environments"][environment]
    lock = RECORD / spec["lock_file"]
    pins = _pins(lock)
    expected = {k: v for k, v in spec["packages"].items() if k != "torch"}
    assert pins == expected
    for name in pins:
        block = lock.read_text(encoding="utf-8").split(f"{name}==", 1)[1].split("\n", 1)[1]
        assert block.lstrip().startswith("--hash=sha256:"), name
    assert MANIFEST["lock_file_sha256"][lock.name] == hashlib.sha256(lock.read_bytes()).hexdigest()


def test_historical_record_is_pinned_to_the_published_runs() -> None:
    assert MANIFEST["runtime"]["python"] == "3.12.16"
    assert MANIFEST["environments"]["inference"]["packages"]["transformers"] == "4.55.4"
    assert MANIFEST["environments"]["inference"]["packages"]["torch"] == "2.7.1+cpu"
    assert MANIFEST["environments"]["aggregate"]["packages"]["numpy"] == "2.2.6"
    assert MANIFEST["environments"]["aggregate-minimal"]["packages"] == {
        "cffi": "2.1.1",
        "cryptography": "46.0.3",
        "pycparser": "3.12",
    }
    assert "numpy" not in MANIFEST["environments"]["aggregate-minimal"]["packages"]
    assert MANIFEST["environments"]["aggregate-minimal"]["forbidden_packages"] == ["numpy", "torch"]
    run_ids = {run["run_id"] for run in MANIFEST["runs"]}
    assert {"42389121599", "42418593837", "42436331559", "42485634513", "42384213361"} <= run_ids
    for run in MANIFEST["runs"]:
        assert re.fullmatch(r"[0-9a-f]{40}", run["head_sha"])


def test_compare_reports_every_mismatch() -> None:
    manifest = {
        "runtime": {"python": "3.12.16"},
        "environments": {"aggregate": {"packages": {"numpy": "2.2.6", "cffi": "2.1.1"}}},
    }
    versions = {"numpy": "2.5.4"}
    problems = compare(manifest, "aggregate", python_version="3.13.1", installed=versions.get)
    assert problems == [
        "python: expected 3.12.16, found 3.13.1",
        "cffi: expected 2.1.1, found missing",
        "numpy: expected 2.2.6, found 2.5.4",
    ]


def test_compare_accepts_exact_environment() -> None:
    manifest = {
        "runtime": {"python": "3.12.16"},
        "environments": {"aggregate": {"packages": {"numpy": "2.2.6"}}},
    }
    assert (
        compare(manifest, "aggregate", python_version="3.12.16", installed={"numpy": "2.2.6"}.get)
        == []
    )


def test_compare_rejects_unknown_environment() -> None:
    with pytest.raises(ValueError, match="unknown environment"):
        compare(MANIFEST, "test-split", python_version="3.12.16", installed=lambda _n: None)


def test_compare_rejects_forbidden_packages_in_minimal_environment() -> None:
    manifest = {
        "runtime": {"python": "3.12.16"},
        "environments": {
            "aggregate-minimal": {
                "packages": {"cffi": "2.1.1"},
                "forbidden_packages": ["numpy", "torch"],
            }
        },
    }
    installed = {"cffi": "2.1.1", "numpy": "2.2.6"}
    problems = compare(
        manifest,
        "aggregate-minimal",
        python_version="3.12.16",
        installed=installed.get,
    )
    assert problems == ["numpy: unexpected package 2.2.6"]
