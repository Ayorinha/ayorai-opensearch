"""Salted commitments for audit-log leaves (ADR-010, owner decision 1).

``commitment = SHA-256(DOMAIN_LABEL || salt || RFC8785(record))``

* ``salt`` is exactly 32 random bytes per event, kept in an erasable,
  access-controlled store and in the client's receipt. Erasing it makes the
  commitment unlinkable to its record while the Merkle tree stays valid.
* ``record`` is a JSON object serialized with RFC 8785 (JCS). Its fields are
  defined by the event schema of a later phase; this module only commits.
* ``DOMAIN_LABEL`` separates these commitments from every other SHA-256 use in
  the project. It is fixed for schema version 1 and must not change; a new
  label means a new schema version.

The verdict is only ever placed inside ``record`` (owner decision 2); nothing
here publishes it.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Mapping
from typing import Any

import rfc8785

DOMAIN_LABEL = b"ayorai-attractor/audit-commitment/v1\x00"
SALT_SIZE = 32

__all__ = ["DOMAIN_LABEL", "SALT_SIZE", "commit", "new_salt", "verify_commitment"]


def new_salt() -> bytes:
    """32 bytes from the operating system CSPRNG."""
    return secrets.token_bytes(SALT_SIZE)


def _preimage(record: Mapping[str, Any], salt: bytes) -> bytes:
    if not isinstance(salt, bytes | bytearray) or len(salt) != SALT_SIZE:
        raise ValueError("salt must be exactly 32 bytes")
    if not isinstance(record, Mapping) or not record:
        raise ValueError("record must be a non-empty JSON object")
    if not all(isinstance(key, str) for key in record):
        raise ValueError("record keys must be strings")
    try:
        canonical = rfc8785.dumps(dict(record))
    except (TypeError, rfc8785.CanonicalizationError) as error:
        raise ValueError(f"record is not RFC 8785 serializable: {error}") from error
    return DOMAIN_LABEL + bytes(salt) + canonical


def commit(record: Mapping[str, Any], salt: bytes) -> bytes:
    """Return the 32-byte commitment of ``record`` under ``salt``."""
    return hashlib.sha256(_preimage(record, salt)).digest()


def verify_commitment(commitment: bytes, record: Mapping[str, Any], salt: bytes) -> bool:
    """Constant-time check; malformed inputs return ``False`` instead of raising."""
    if not isinstance(commitment, bytes | bytearray) or len(commitment) != 32:
        return False
    try:
        expected = commit(record, salt)
    except ValueError:
        return False
    return hmac.compare_digest(expected, bytes(commitment))
