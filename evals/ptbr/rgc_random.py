"""RGC-PRNG-1 and the type-7 percentile interval (DEC-027, D2 and D3).

Every random draw of the RGC statistics comes from this module, so the runner, the
agreement tool and the sign-flip test cannot drift apart. The generator is specified
byte for byte in DEC-027 (docs/DECISIONS-PENDING.md) and depends only on SHA-256: a
third party can reproduce every draw from the text, without Python's random module or
NumPy, whose streams are not guaranteed across versions.

This is a deterministic pseudorandom stream for statistical reproducibility only. It is
not a cryptographic DRBG and must never be used for secrets, keys, tokens, nonces or
security-sensitive randomness. It has no entropy input, reseeding or prediction-resistance
mechanism and has not been validated under NIST SP 800-90A.

Block i = SHA-256("AYORAI-RGC-PRNG-1" || 0x00 || u32be(len(label)) || label
                  || u64be(seed) || u64be(i)); each block yields eight big-endian u32
words, consumed in order with one continuous cursor per stream. A uniform integer in
[0, n) rejects words >= 2^32 - (2^32 mod n), so there is no modulo bias.
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
from collections.abc import Sequence
from fractions import Fraction

DOMAIN = b"AYORAI-RGC-PRNG-1"
RGC_SEED = 20261003
_LABEL_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_WORDS_PER_BLOCK = 8
_MAX_COUNTER = 2**64 - 1

# One stream per procedure (DEC-027, D3): a change in how many draws one procedure
# makes never shifts the draws of another.
LABEL_CLUSTER_ACCURACY = "dec019-accuracy-bootstrap"
LABEL_COMPONENT_ACCURACY = "dec023-accuracy-bootstrap"
LABEL_CASE_ACCURACY = "case-accuracy-bootstrap"
LABEL_SIGN_FLIP = "dec021-sign-flip"
LABEL_COMPONENT_KAPPA = "dec022-kappa-bootstrap"
LABEL_CASE_KAPPA = "case-kappa-bootstrap"

LOWER = Fraction(1, 40)  # 0.025
UPPER = Fraction(39, 40)  # 0.975


class RgcPrng:
    """One RGC-PRNG-1 stream for one (seed, label) pair."""

    def __init__(self, seed: int, label: str) -> None:
        if type(seed) is not int or not 0 <= seed < 2**64:
            raise ValueError("seed must be an integer in [0, 2^64)")
        if not isinstance(label, str) or len(label) > 64 or not _LABEL_RE.fullmatch(label):
            raise ValueError(
                "label must match [a-z0-9]+(-[a-z0-9]+)* and have at most 64 characters"
            )
        encoded = label.encode("ascii")
        self._prefix = (
            DOMAIN + b"\x00" + struct.pack(">I", len(encoded)) + encoded + struct.pack(">Q", seed)
        )
        self._counter = 0
        self._words: list[int] = []
        self._position = 0

    @property
    def prefix(self) -> bytes:
        """Bytes hashed before the 8-byte counter (published as a reference vector)."""

        return self._prefix

    @property
    def blocks_used(self) -> int:
        return self._counter

    def block(self, counter: int) -> bytes:
        if type(counter) is not int or not 0 <= counter <= _MAX_COUNTER:
            raise OverflowError("RGC-PRNG-1 block counter out of range")
        return hashlib.sha256(self._prefix + struct.pack(">Q", counter)).digest()

    def word(self) -> int:
        if self._position == len(self._words):
            if self._counter > _MAX_COUNTER:
                raise OverflowError("RGC-PRNG-1 block counter exhausted")
            self._words = list(struct.unpack(">8I", self.block(self._counter)))
            self._counter += 1
            self._position = 0
        value = self._words[self._position]
        self._position += 1
        return value

    def below(self, n: int) -> int:
        """Uniform integer in [0, n) by rejection; rejected words are discarded."""

        if type(n) is not int or not 1 <= n <= 2**32:
            raise ValueError("n must be an integer in [1, 2^32]")
        limit = 2**32 - (2**32 % n)
        while True:
            value = self.word()
            if value < limit:
                return value % n

    def sign(self) -> int:
        """+1 for a draw of 0 and -1 for a draw of 1 from [0, 2)."""

        return 1 if self.below(2) == 0 else -1


def quantile_type7(values: Sequence[float], p: Fraction) -> float:
    """Hyndman-Fan type 7 quantile, h = (n - 1) * p computed exactly (DEC-027, D2)."""

    if not values:
        raise ValueError("quantile requires at least one value")
    if not isinstance(p, Fraction) or not 0 <= p <= 1:
        raise ValueError("p must be a Fraction in [0, 1]")
    ordered = sorted(values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("values must be finite")
    h = (len(ordered) - 1) * p
    j = math.floor(h)
    g = h - j
    lower = ordered[j]
    if g == 0:
        return float(lower)
    return float(lower + float(g) * (ordered[j + 1] - lower))


def percentile_ci95(values: Sequence[float]) -> list[float] | None:
    """[Q(1/40), Q(39/40)] of the defined replicates, or None when there are none."""

    if not values:
        return None
    return [quantile_type7(values, LOWER), quantile_type7(values, UPPER)]
