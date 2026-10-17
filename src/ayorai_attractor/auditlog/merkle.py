"""RFC 6962 / RFC 9162 Merkle tree hashing, inclusion and consistency proofs.

Pure functions over in-memory leaf hashes. This is phase 1 of ADR-010: no
storage, no API, no Judge dependency. Storage, checkpoints and signatures
come in later phases.

Hashing (RFC 6962 §2.1, SHA-256):

* ``leaf_hash(d)  = SHA-256(0x00 || d)``
* ``node_hash(l, r) = SHA-256(0x01 || l || r)``
* the root of the empty tree is ``SHA-256("")``.

Proof generation follows the PATH and SUBPROOF definitions of RFC 6962 §2.1.1
and §2.1.2; verification follows the algorithms of RFC 9162 §2.1.3.2 and
§2.1.4.2. Verification never raises on malformed input: it returns ``False``.

Input contract of the verifiers: hashes (leaf, roots, proof nodes) are
``bytes`` or ``bytearray`` of exactly 32 bytes; a proof is a ``list`` or
``tuple`` of such hashes; indices and sizes are ``int`` (``bool`` rejected).
Anything else, including ``memoryview`` and ``str``, is malformed.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Sequence

HASH_SIZE = 32
LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"

__all__ = [
    "HASH_SIZE",
    "consistency_proof",
    "empty_root",
    "inclusion_proof",
    "leaf_hash",
    "root_from_inclusion",
    "tree_root",
    "verify_consistency",
    "verify_inclusion",
]


def empty_root() -> bytes:
    return hashlib.sha256(b"").digest()


def leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(LEAF_PREFIX + bytes(data)).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    """Interior node hash. Callers pass validated 32-byte digests; not a public verifier."""
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _split(n: int) -> int:
    """Largest power of two strictly smaller than ``n`` (``n >= 2``)."""
    return 1 << ((n - 1).bit_length() - 1)


def _check_hashes(hashes: Sequence[bytes]) -> None:
    for item in hashes:
        if not isinstance(item, bytes | bytearray) or len(item) != HASH_SIZE:
            raise ValueError("every hash must be 32 bytes")


def _mth(hashes: Sequence[bytes]) -> bytes:
    n = len(hashes)
    if n == 0:
        return empty_root()
    if n == 1:
        return bytes(hashes[0])
    k = _split(n)
    return node_hash(_mth(hashes[:k]), _mth(hashes[k:]))


def tree_root(leaf_hashes: Sequence[bytes]) -> bytes:
    """Merkle Tree Hash of a list of already-hashed leaves."""
    _check_hashes(leaf_hashes)
    return _mth(leaf_hashes)


def _path(index: int, hashes: Sequence[bytes]) -> list[bytes]:
    n = len(hashes)
    if n == 1:
        return []
    k = _split(n)
    if index < k:
        return [*_path(index, hashes[:k]), _mth(hashes[k:])]
    return [*_path(index - k, hashes[k:]), _mth(hashes[:k])]


def inclusion_proof(index: int, leaf_hashes: Sequence[bytes]) -> list[bytes]:
    """Audit path for leaf ``index`` in the tree made of ``leaf_hashes``."""
    _check_hashes(leaf_hashes)
    if not _is_int(index) or not 0 <= index < len(leaf_hashes):
        raise ValueError("index must be inside the tree")
    return _path(index, leaf_hashes)


def _subproof(m: int, hashes: Sequence[bytes], complete: bool) -> list[bytes]:
    n = len(hashes)
    if m == n:
        return [] if complete else [_mth(hashes)]
    k = _split(n)
    if m <= k:
        return [*_subproof(m, hashes[:k], complete), _mth(hashes[k:])]
    return [*_subproof(m - k, hashes[k:], False), _mth(hashes[:k])]


def consistency_proof(size1: int, leaf_hashes: Sequence[bytes]) -> list[bytes]:
    """Proof that the first ``size1`` leaves form a prefix of the whole tree."""
    _check_hashes(leaf_hashes)
    if not _is_int(size1) or not 0 < size1 <= len(leaf_hashes):
        raise ValueError("size1 must satisfy 0 < size1 <= size2")
    if size1 == len(leaf_hashes):
        return []
    return _subproof(size1, leaf_hashes, True)


def _is_int(value: object) -> bool:
    """True for real integers only; ``bool`` is a subclass of ``int`` and is rejected."""
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_proof(proof: object) -> bool:
    """A proof is a list or tuple of 32-byte hashes; anything else is malformed."""
    return isinstance(proof, list | tuple) and all(_valid_hash(p) for p in proof)


def _valid_hash(value: object) -> bool:
    return isinstance(value, bytes | bytearray) and len(value) == HASH_SIZE


def root_from_inclusion(index: int, size: int, leaf: bytes, proof: Sequence[bytes]) -> bytes | None:
    """RFC 9162 §2.1.3.2: recompute the root, or ``None`` if the proof is malformed."""
    if not (_is_int(index) and _is_int(size)) or not 0 <= index < size:
        return None
    if not _valid_hash(leaf) or not _valid_proof(proof):
        return None
    fn, sn = index, size - 1
    r = bytes(leaf)
    for p in proof:
        if sn == 0:
            return None
        if fn & 1 or fn == sn:
            r = node_hash(bytes(p), r)
            if not fn & 1:
                while fn & 1 == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node_hash(r, bytes(p))
        fn >>= 1
        sn >>= 1
    if sn != 0:
        return None
    return r


def verify_inclusion(
    index: int, size: int, leaf: bytes, proof: Sequence[bytes], root: bytes
) -> bool:
    computed = root_from_inclusion(index, size, leaf, proof)
    return computed is not None and _valid_hash(root) and hmac.compare_digest(computed, root)


def verify_consistency(
    size1: int, size2: int, root1: bytes, root2: bytes, proof: Sequence[bytes]
) -> bool:
    """RFC 9162 §2.1.4.2 consistency verification between two tree heads."""
    if not (_is_int(size1) and _is_int(size2)):
        return False
    if not (_valid_hash(root1) and _valid_hash(root2)):
        return False
    if not _valid_proof(proof):
        return False
    # As in the transparency-dev reference: a proof from the empty tree is
    # meaningless and is rejected rather than trivially accepted.
    if size1 <= 0 or size2 < size1:
        return False
    if size1 == size2:
        return len(proof) == 0 and hmac.compare_digest(bytes(root1), bytes(root2))
    if not proof:
        return False
    path = [bytes(p) for p in proof]
    if size1 & (size1 - 1) == 0:  # size1 is an exact power of two
        path.insert(0, bytes(root1))
    fn, sn = size1 - 1, size2 - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr = node_hash(c, fr)
            sr = node_hash(c, sr)
            if not fn & 1:
                while fn & 1 == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = node_hash(sr, c)
        fn >>= 1
        sn >>= 1
    return (
        sn == 0 and hmac.compare_digest(fr, bytes(root1)) and hmac.compare_digest(sr, bytes(root2))
    )
