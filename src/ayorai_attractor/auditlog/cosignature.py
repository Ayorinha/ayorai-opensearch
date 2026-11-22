"""C2SP tlog-cosignature v1.1.0: timestamped Ed25519 checkpoint cosignatures.

Separate from note.py: log signatures use type 0x01; witness signatures use
type 0x04 and a timestamped signature structure.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import time
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

COSIGNATURE_TYPE = b"\x04"
_SIGNATURE_PREFIX = "— "
_MAX_TIMESTAMP = (1 << 64) - 1


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 255:
        raise ValueError("cosigner name must be 1-255 UTF-8 bytes")
    if any(
        char.isspace()
        or char == "+"
        or ord(char) < 0x20
        or unicodedata.category(char) == "Zs"
        for char in name
    ):
        raise ValueError("cosigner name must not contain Unicode spaces, '+', or control characters")


def _public_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def key_id(name: str, public_key: bytes) -> bytes:
    """SHA-256(name || LF || 0x04 || public_key)[:4], as specified by C2SP."""
    _validate_name(name)
    if not isinstance(public_key, bytes) or len(public_key) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    return hashlib.sha256(name.encode("utf-8") + b"\n" + COSIGNATURE_TYPE + public_key).digest()[:4]


def signed_message(checkpoint_body: str, timestamp: int) -> bytes:
    """Build the C2SP cosignature/v1 message; body includes its final newline."""
    if not isinstance(checkpoint_body, str) or not checkpoint_body.endswith("\n"):
        raise ValueError("checkpoint body must end with a newline")
    if (
        not isinstance(timestamp, int)
        or isinstance(timestamp, bool)
        or not 0 <= timestamp <= _MAX_TIMESTAMP
    ):
        raise ValueError("timestamp must be an unsigned 64-bit POSIX integer")
    return f"cosignature/v1\ntime {timestamp}\n{checkpoint_body}".encode()


def sign_cosignature(
    name: str, seed: bytes, checkpoint_body: str, timestamp: int | None = None
) -> str:
    """Create one C2SP Ed25519 (0x04) signature line for a checkpoint body."""
    _validate_name(name)
    if not isinstance(seed, bytes) or len(seed) != 32:
        raise ValueError("Ed25519 seed must be exactly 32 bytes")
    timestamp = int(time.time()) if timestamp is None else timestamp
    message = signed_message(checkpoint_body, timestamp)
    private_key = Ed25519PrivateKey.from_private_bytes(seed)
    public_key = _public_bytes(private_key.public_key())
    payload = key_id(name, public_key) + timestamp.to_bytes(8, "big") + private_key.sign(message)
    return f"{_SIGNATURE_PREFIX}{name} {base64.b64encode(payload).decode('ascii')}\n"


def verify_cosignature(
    note: str,
    name: str,
    public_key: bytes,
    *,
    now: int | None = None,
    max_future_skew: int = 300,
) -> bool:
    """Verify a matching 0x04 line; unknown cosigners and malformed lines are ignored."""
    try:
        expected_id = key_id(name, public_key)
        if (
            not isinstance(note, str)
            or not isinstance(max_future_skew, int)
            or isinstance(max_future_skew, bool)
            or max_future_skew < 0
            or (
                now is not None
                and (
                    not isinstance(now, int)
                    or isinstance(now, bool)
                    or not 0 <= now <= _MAX_TIMESTAMP
                )
            )
        ):
            return False
        separator = note.rfind("\n\n")
        if separator < 0:
            return False
        body = note[: separator + 1]
        signature_text = note[separator + 2 :]
        if not signature_text.endswith("\n"):
            return False
        verifier = Ed25519PublicKey.from_public_bytes(public_key)
        current_time = int(time.time()) if now is None else now
        for line in signature_text[:-1].split("\n"):
            if not line.startswith(_SIGNATURE_PREFIX):
                continue
            fields = line[len(_SIGNATURE_PREFIX) :].split(" ")
            if len(fields) != 2 or fields[0] != name:
                continue
            try:
                raw = base64.b64decode(fields[1], validate=True)
            except (ValueError, binascii.Error):
                continue
            if base64.b64encode(raw).decode("ascii") != fields[1]:
                continue
            if len(raw) != 4 + 8 + 64 or raw[:4] != expected_id:
                continue
            timestamp = int.from_bytes(raw[4:12], "big")
            if (
                timestamp > _MAX_TIMESTAMP
                or timestamp > current_time + max_future_skew
            ):
                continue
            verifier.verify(raw[12:], signed_message(body, timestamp))
            return True
    except (ValueError, TypeError, InvalidSignature):
        return False
    return False
