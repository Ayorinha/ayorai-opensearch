"""Versioned, deterministic digest for semantic evaluation results.

The semantic digest is intentionally separate from the legacy content_sha256.
The only excluded keys are the explicit, closed set: latency_ms, git_sha,
content_sha256, and semantic_sha256. Each is excluded because it is execution
metadata or a digest of the same report rather than semantic evaluation data.
Any additional volatile field must be added explicitly in a reviewed change
with a documented justification; never infer volatility from key-name patterns.
Keep semantic_digest_version in the canonical payload so digest-version changes
are explicit.

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
    }
)


def _is_volatile_key(key: str) -> bool:
    """Return whether a key is in the explicitly approved volatile-field set."""
    return key in _VOLATILE_KEYS


def _without_volatile_fields(value: Any) -> Any:
    """Recursively remove only explicitly approved volatile keys."""
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

    Only latency_ms, git_sha, content_sha256, and semantic_sha256 are removed,
    recursively at every nesting level. All other fields—including evidence
    retrieval, publication, and collection dates—remain semantic inputs.
    """
    canonical = json.dumps(
        _without_volatile_fields(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
