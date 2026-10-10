"""Shared test-process isolation for local runtime persistence.

The API module creates its default audit store at import time. Keep that
collection-time store in memory; tests that exercise persistence explicitly
use tmp_path and monkeypatch their store instance.
"""
import os

os.environ["ATTRACTOR_AUDIT_DB"] = ":memory:"
