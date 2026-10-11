"""Exact-known-secret leakage checks for response-shaped data.

These helpers detect leakage of an exact, known secret; they are not a generic
credential detector. Document text is treated as data. The helpers do not
rewrite, remove, or downgrade factual evidence merely because an excerpt
contains instruction-like text.
"""

from dataclasses import asdict, is_dataclass
from pydantic import BaseModel


def contains_secret(value: object, secret: str) -> bool:
    """Recursively detect an exact, non-empty secret in response-shaped data."""
    if not secret:
        raise ValueError("secret must be non-empty")
    if isinstance(value, str):
        return secret in value
    if isinstance(value, (bytes, bytearray)):
        return secret.encode("utf-8") in value
    if isinstance(value, BaseModel):
        return contains_secret(value.model_dump(mode="python"), secret)
    if is_dataclass(value) and not isinstance(value, type):
        return contains_secret(asdict(value), secret)
    if isinstance(value, dict):
        return any(
            contains_secret(k, secret) or contains_secret(v, secret)
            for k, v in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(contains_secret(item, secret) for item in value)
    return False


def assert_no_secret(value: object, secret: str) -> None:
    """Raise when an evaluation secret appears in any response field."""
    if contains_secret(value, secret):
        raise ValueError("response contains an evaluation secret")
