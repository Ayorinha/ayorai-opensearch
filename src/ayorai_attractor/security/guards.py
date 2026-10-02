"""Deterministic boundary checks for untrusted agent inputs.

These checks classify instruction-like text as untrusted data. They do not
execute, rewrite, or silently discard evidence.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    message: str


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all|any|the)\s+(?:previous|prior|above)\s+instructions", re.I),
    re.compile(r"system\s+message\s*:", re.I),
    re.compile(r"developer\s+message\s*:", re.I),
    re.compile(r"reveal\s+(?:the\s+)?(?:system|developer)\s+prompt", re.I),
    re.compile(r"send\s+(?:the\s+)?(?:secret|credentials|token|api\s+key)", re.I),
)


def scan_untrusted_text(text: str) -> tuple[SecurityFinding, ...]:
    """Return deterministic findings for common instruction-injection markers."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    findings: list[SecurityFinding] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(
                SecurityFinding(
                    code="PROMPT_INJECTION_MARKER",
                    message="Instruction-like text must be treated as untrusted data.",
                )
            )
    return tuple(findings)


def assert_no_secret(value: object, secret: str) -> None:
    """Reject a known evaluation secret anywhere in response-shaped data."""
    if not secret:
        raise ValueError("secret must not be empty")
    if _contains(value, secret):
        raise ValueError("response contains an evaluation secret")


def _contains(value: object, secret: str) -> bool:
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(_contains(k, secret) or _contains(v, secret) for k, v in value.items())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains(item, secret) for item in value)
    return False
