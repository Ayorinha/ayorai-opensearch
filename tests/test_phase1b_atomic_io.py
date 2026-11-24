"""Atomic file-write guarantees for private Phase 1b artifacts."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from scripts.benchmarks.phase1b import common
from scripts.benchmarks.phase1b.common import atomic_write_bytes


def test_atomic_write_creates_restrictive_file_and_replaces_contents(
    tmp_path: Path,
) -> None:
    target = tmp_path / "private" / "artifact.bin"
    target.parent.mkdir()
    target.write_bytes(b"old")

    atomic_write_bytes(target, b"new-private-payload")

    assert target.read_bytes() == b"new-private-payload"
    if os.name == "posix":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(target.parent.glob(".*.tmp")) == []


def test_atomic_write_preserves_previous_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"known-good")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(common.os, "replace", fail_replace)
    with pytest.raises(OSError, match="synthetic replace failure"):
        atomic_write_bytes(target, b"must-not-partially-replace")

    assert target.read_bytes() == b"known-good"
    assert list(tmp_path.glob(".*.tmp")) == []
