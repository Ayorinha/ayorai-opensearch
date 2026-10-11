"""Versioned deterministic Judge 2.0.0 rule-contract loader.

This module loads the normative rule data and computes its content identity.
It does not yet replace the legacy r1-a judge or adjudicate claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

RULES_VERSION = "2.0.0"
_RULES_PATH = Path(__file__).resolve().parents[4] / "rules" / "judge-2.0.0.json"


class JudgeRulesError(ValueError):
    """Raised when the versioned Judge rules are missing or malformed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON using the ADR-009 canonical encoding."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def load_rules(path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    """Load Judge 2.0.0 rules and return the document plus its SHA-256.

    The digest is calculated over the exact UTF-8 bytes stored in the file,
    including the final newline, so it identifies the reviewed artifact.
    """
    rules_path = Path(path) if path is not None else _RULES_PATH
    try:
        raw = rules_path.read_bytes()
        rules = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JudgeRulesError(f"cannot load Judge rules from {rules_path}") from exc
    if not isinstance(rules, dict):
        raise JudgeRulesError("Judge rules document must be a JSON object")
    if rules.get("judge_rules_version") != RULES_VERSION:
        raise JudgeRulesError("unsupported Judge rules version")
    if rules.get("schema_version") != "judge-rules/2.0.0":
        raise JudgeRulesError("unsupported Judge rules schema")
    return rules, hashlib.sha256(raw).hexdigest()


def rules_sha256(path: str | Path | None = None) -> str:
    """Return the content SHA-256 for the selected Judge rules artifact."""
    return load_rules(path)[1]


__all__ = [
    "JudgeRulesError",
    "RULES_VERSION",
    "canonical_json_bytes",
    "load_rules",
    "rules_sha256",
]
