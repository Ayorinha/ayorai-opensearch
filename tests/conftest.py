"""Shared test-process isolation for local runtime persistence.

The API module creates its default audit store at import time. During tests,
ATTRACTOR_AUDIT_DB is deliberately overridden with ":memory:" before the API
module is imported; tests that exercise persistence explicitly use tmp_path
and monkeypatch their store instance.
"""
import hashlib
import os
from pathlib import Path
from typing import Iterator

import pytest

# This runs before test modules import the API application.
os.environ["ATTRACTOR_AUDIT_DB"] = ":memory:"

Snapshot = dict[str, tuple[int, int, str]]


def snapshot_runtime_data(directory: Path) -> tuple[bool, Snapshot]:
    """Capture existence and file size/mtime/content hash for .attractor/."""
    if not directory.exists():
        return False, {}
    files: Snapshot = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            data = path.read_bytes()
            stat = path.stat()
            files[relative] = (
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(data).hexdigest(),
            )
    return True, files


def runtime_data_changes(
    before: tuple[bool, Snapshot], after: tuple[bool, Snapshot]
) -> list[str]:
    """Describe only runtime data created, modified, or removed during a test session."""
    existed_before, old_files = before
    exists_after, new_files = after
    changes: list[str] = []
    if not existed_before and exists_after:
        changes.append(".attractor/ directory created during the test session")
    for name in sorted(new_files.keys() - old_files.keys()):
        changes.append(f".attractor/{name} created")
    for name in sorted(old_files.keys() - new_files.keys()):
        changes.append(f".attractor/{name} removed")
    for name in sorted(old_files.keys() & new_files.keys()):
        if old_files[name] != new_files[name]:
            changes.append(f".attractor/{name} modified (size/mtime/content hash changed)")
    return changes


@pytest.fixture(scope="session", autouse=True)
def assert_no_repository_runtime_data() -> Iterator[None]:
    """Fail only on .attractor/ changes during tests, preserving pre-existing data."""
    repository_root = Path(__file__).resolve().parents[1]
    directory = repository_root / ".attractor"
    before = snapshot_runtime_data(directory)
    yield
    after = snapshot_runtime_data(directory)
    changes = runtime_data_changes(before, after)
    message = "Repository runtime data changed during tests:\n- " + "\n- ".join(changes)
    assert not changes, message
