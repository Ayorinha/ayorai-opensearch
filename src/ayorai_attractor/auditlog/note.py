"""C2SP signed notes and transparency-log checkpoints with Ed25519 (ADR-010, phase 2).

Formats (c2sp.org/signed-note v1.0.0 and c2sp.org/tlog-checkpoint v1.0.0):

* checkpoint body: ``<origin>\\n<tree size>\\n<base64 root hash>\\n``;
* signed note: ``<body>\\n`` followed by one line per signature,
  ``— <key name> <base64(key hash (4 bytes) || signature)>\\n``;
* Ed25519 key hash: ``SHA-256(<key name> || 0x0A || 0x01 || public key)[:4]``;
* verifier key: ``<key name>+<hex key hash>+<base64(0x01 || public key)>``.

Signing and verification use the ``cryptography`` package; nothing here is
home-grown cryptography (ADR-010, requirement 6).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

ED25519_TYPE = b"\x01"
_SIGNATURE_PREFIX = "— "
_KEY_NAME = re.compile(r"[\x21-\x2a\x2c-\x7e]+")  # printable ASCII without '+' and spaces

__all__ = [
    "Checkpoint",
    "NoteSigner",
    "parse_checkpoint",
    "verifier_key",
    "verify_note",
]


def _key_hash(name: str, public_key: bytes) -> bytes:
    return hashlib.sha256(name.encode("utf-8") + b"\n" + ED25519_TYPE + public_key).digest()[:4]


def _public_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class NoteSigner:
    """Signs notes with one Ed25519 key under one key name (the log origin)."""

    def __init__(self, name: str, seed: bytes) -> None:
        if _KEY_NAME.fullmatch(name) is None:
            raise ValueError("key name must be printable ASCII without spaces or '+'")
        if not isinstance(seed, bytes) or len(seed) != 32:
            raise ValueError("Ed25519 seed must be exactly 32 bytes")
        self.name = name
        self._key = Ed25519PrivateKey.from_private_bytes(seed)
        self.public_key = _public_bytes(self._key.public_key())
        self.key_hash = _key_hash(name, self.public_key)

    @property
    def verifier_key(self) -> str:
        return verifier_key(self.name, self.public_key)

    def sign(self, body: str) -> str:
        if not body.endswith("\n") or "\n\n" in body:
            raise ValueError("note body must end with one newline and contain no blank line")
        signature = self._key.sign(body.encode("utf-8"))
        encoded = base64.b64encode(self.key_hash + signature).decode("ascii")
        return f"{body}\n{_SIGNATURE_PREFIX}{self.name} {encoded}\n"


def verifier_key(name: str, public_key: bytes) -> str:
    key_hash = _key_hash(name, public_key)
    encoded = base64.b64encode(ED25519_TYPE + public_key).decode("ascii")
    return f"{name}+{key_hash.hex()}+{encoded}"


def _parse_verifier_key(vkey: str) -> tuple[str, bytes, bytes] | None:
    # The base64 key may itself contain "+": split at the first two only.
    parts = vkey.split("+", 2)
    if len(parts) != 3 or _KEY_NAME.fullmatch(parts[0]) is None:
        return None
    try:
        key_hash = bytes.fromhex(parts[1])
        raw = base64.b64decode(parts[2], validate=True)
    except (ValueError, binascii.Error):
        return None
    if len(key_hash) != 4 or len(raw) != 33 or raw[:1] != ED25519_TYPE:
        return None
    public_key = raw[1:]
    if _key_hash(parts[0], public_key) != key_hash:
        return None
    return parts[0], key_hash, public_key


def verify_note(note: str, vkey: str) -> str | None:
    """Return the note body if it carries a valid signature by ``vkey``, else ``None``."""
    parsed = _parse_verifier_key(vkey)
    if parsed is None or not isinstance(note, str):
        return None
    name, key_hash, public_key = parsed
    separator = note.rfind("\n\n")
    if separator < 0:
        return None
    body = note[: separator + 1]
    signatures = note[separator + 2 :]
    if not signatures.endswith("\n"):
        return None
    verifier = Ed25519PublicKey.from_public_bytes(public_key)
    for line in signatures[:-1].split("\n"):
        if not line.startswith(_SIGNATURE_PREFIX):
            return None
        fields = line[len(_SIGNATURE_PREFIX) :].split(" ")
        if len(fields) != 2 or fields[0] != name:
            continue
        try:
            raw = base64.b64decode(fields[1], validate=True)
        except (ValueError, binascii.Error):
            continue
        if len(raw) != 4 + 64 or raw[:4] != key_hash:
            continue
        try:
            verifier.verify(raw[4:], body.encode("utf-8"))
        except InvalidSignature:
            continue
        return body
    return None


@dataclass(frozen=True)
class Checkpoint:
    origin: str
    size: int
    root: bytes

    def body(self) -> str:
        return f"{self.origin}\n{self.size}\n{base64.b64encode(self.root).decode('ascii')}\n"


def parse_checkpoint(body: str) -> Checkpoint | None:
    """Parse a checkpoint body (extension lines are not used by this log)."""
    lines = body.split("\n")
    if len(lines) != 4 or lines[3] != "" or not lines[0]:
        return None
    if re.fullmatch(r"0|[1-9][0-9]*", lines[1]) is None:
        return None
    try:
        root = base64.b64decode(lines[2], validate=True)
    except (ValueError, binascii.Error):
        return None
    if len(root) != 32:
        return None
    return Checkpoint(lines[0], int(lines[1]), root)
