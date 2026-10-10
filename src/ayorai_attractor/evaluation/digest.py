"""Versioned, deterministic digest for semantic evaluation results.

The semantic digest is intentionally separate from the legacy content_sha256.
Recursively exclude execution-volatile metadata: latency_ms, git_sha,
content_sha256, semantic_sha256, and wall-clock fields (timestamp/datetime
keys and keys ending in _at or _time). These values can vary between equivalent
runs and are not part of the evaluated result. Keep semantic_digest_version in
the canonical payload so digest-version changes are explicit.

Canonicalization is UTF-8 JSON with sorted keys, compact separators, and
ensure_ascii=False. This module is pure: it performs no I/O and reads no clock,
environment, network, or repository metadata.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

SEMANTIC_DIGEST_VERSION = "1"

_VOLATILE_KEYS = frozenset(
    {
        "latency_ms",
        "git_sha",
        "content_sha256",
        "semantic_sha256",
        "time",
        "timestamp",
        "datetime",
        "date_time",
        "wall_clock_time",
        "wallclock_time",
        "execution_time",
        "elapsed_time",
        "duration_time",
        "elapsed_ms",
        "duration_ms",
        "runtime_ms",
    }
)


def _is_volatile_key(key: str) -> bool:
    """Return whether a field is execution-specific rather than semantic."""
    normalized = key.casefold().replace("-", "_")
    return (
        normalized in _VOLATILE_KEYS
        or normalized.endswith(("_at", "_time", "_timestamp", "_datetime"))
        or normalized.endswith(("timestamp", "datetime"))
    )


def _without_volatile_fields(value: Any) -> Any:
    """Recursively remove execution-volatile keys from JSON-compatible data."""
    if isinstance(value, Mapping):
        return {
            key: _without_volatile_fields(item)
            for key, item in value.items()
            if not _is_volatile_key(str(key))
        }
    if isinstance(value, list):
        return [_without_volatile_fields(item) for item in value]
    if isinstance(value, tuple):
        return [_without_volatile_fields(item) for item in value]
    return value


def semantic_sha256(report: Mapping[str, Any]) -> str:
    """Hash semantic report content using canonical UTF-8 JSON.

    Volatile fields are removed recursively at every nesting level. Semantic
    fields such as predictions, expected labels, metrics, and the digest
    version remain part of the hash. The caller should set
    semantic_digest_version before computing this digest.
    """
    canonical = json.dumps(
        _without_volatile_fields(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
