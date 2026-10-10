"""Shared test-process isolation for local runtime persistence.

The API module creates its default audit store at import time. Keep that
collection-time store in memory; tests that exercise persistence explicitly
use tmp_path and monkeypatch their store instance.
"""
import os
from pathlib import Path

import pytest

# This runs before test modules import the API application.
os.environ["ATTRACTOR_AUDIT_DB"] = ":memory:"


@pytest.fixture(scope="session", autouse=True)
def assert_no_repository_runtime_data():
    """A clean test run must not create local audit/replay data in the repo."""
    yield
    repository_root = Path(__file__).resolve().parents[1]
    assert not (repository_root / ".attractor").exists(), (
        "Tests created .attractor/ in the repository root; isolate runtime "
        "audit and replay storage in memory or under tmp_path."
    )
