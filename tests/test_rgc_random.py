"""RGC-PRNG-1 and type-7 percentile (DEC-027, D2 and D3): reference vectors."""

from __future__ import annotations

import hashlib
import struct
from fractions import Fraction

import pytest

from evals.ptbr import rgc_random
from evals.ptbr.rgc_random import RgcPrng, percentile_ci95, quantile_type7

SEED = 20261003


def test_reference_prefix_and_block_zero() -> None:
    stream = RgcPrng(SEED, "dec022-kappa-bootstrap")
    assert stream.prefix.hex() == (
        "41594f5241492d5247432d50524e472d3100000000166465633032322d6b617070612d626f6f7473"
        "74726170000000000135288b"
    )
    assert stream.block(0).hex() == (
        "3f7b4515d60d21e0d80074db4286b9d2ff821ad0e67c8d2e2209fbae17bd2498"
    )
    # Independent of the class: the block is SHA-256 of prefix || u64be(0).
    assert stream.block(0) == hashlib.sha256(stream.prefix + struct.pack(">Q", 0)).digest()


def test_reference_draws() -> None:
    kappa = RgcPrng(SEED, "dec022-kappa-bootstrap")
    assert [kappa.below(10) for _ in range(12)] == [1, 4, 1, 0, 4, 6, 8, 0, 6, 8, 1, 5]
    accuracy = RgcPrng(SEED, "dec019-accuracy-bootstrap")
    assert [accuracy.below(7) for _ in range(12)] == [6, 3, 5, 4, 2, 4, 2, 2, 1, 4, 5, 6]
    flips = RgcPrng(SEED, "dec021-sign-flip")
    signs = "".join("+" if flips.sign() == 1 else "-" for _ in range(16))
    assert signs == "-+---++------+--"


def test_rejection_discards_words_without_reusing_them() -> None:
    stream = RgcPrng(0, "rejection-check")
    words = struct.unpack(">8I", stream.block(0))
    limit = 2**32 - (2**32 % (2**31 + 1))
    assert [w for w in words[:5] if w >= limit] == [3518580100, 4222768487]
    assert [stream.below(2**31 + 1) for _ in range(3)] == [1182218569, 1800520938, 1786065899]
    assert stream.blocks_used == 1


def test_word_cursor_is_continuous_across_operations_and_blocks() -> None:
    stream = RgcPrng(SEED, "dec022-kappa-bootstrap")
    words = [stream.word() for _ in range(20)]
    expected = [
        *struct.unpack(">8I", stream.block(0)),
        *struct.unpack(">8I", stream.block(1)),
        *struct.unpack(">8I", stream.block(2)),
    ][:20]
    assert words == expected
    assert stream.blocks_used == 3


def test_streams_are_separated_by_label() -> None:
    first = RgcPrng(SEED, rgc_random.LABEL_CLUSTER_ACCURACY)
    second = RgcPrng(SEED, rgc_random.LABEL_COMPONENT_ACCURACY)
    assert first.block(0) != second.block(0)


@pytest.mark.parametrize("label", ["", "Upper", "under_score", "a--b", "-a", "a" * 65, "çã"])
def test_invalid_labels_are_rejected(label: str) -> None:
    with pytest.raises(ValueError, match="label"):
        RgcPrng(SEED, label)


@pytest.mark.parametrize("seed", [-1, 2**64, True])
def test_invalid_seeds_are_rejected(seed: int) -> None:
    with pytest.raises(ValueError, match="seed"):
        RgcPrng(seed, "dec021-sign-flip")


def test_range_and_counter_limits() -> None:
    stream = RgcPrng(SEED, "dec021-sign-flip")
    with pytest.raises(ValueError, match="n must"):
        stream.below(0)
    with pytest.raises(ValueError, match="n must"):
        stream.below(2**32 + 1)
    assert stream.below(1) == 0
    with pytest.raises(OverflowError):
        stream.block(2**64)

    stream._counter = 2**64 - 1
    assert len([stream.word() for _ in range(8)]) == 8
    with pytest.raises(OverflowError, match="counter exhausted"):
        stream.word()


def test_quantile_type7_by_hand() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    # h = 4 * 1/40 = 0.1 -> 10 + 0.1 * 10; h = 4 * 39/40 = 3.9 -> 40 + 0.9 * 10
    assert quantile_type7(values, Fraction(1, 40)) == pytest.approx(11.0)
    assert quantile_type7(values, Fraction(39, 40)) == pytest.approx(49.0)
    assert quantile_type7(values, Fraction(0)) == 10.0
    assert quantile_type7(values, Fraction(1)) == 50.0
    assert quantile_type7([7.0], Fraction(1, 40)) == 7.0
    # n - 1 a multiple of 40: h is an integer and no interpolation happens.
    exact = [float(i) for i in range(41)]
    assert quantile_type7(exact, Fraction(1, 40)) == 1.0
    assert quantile_type7(exact, Fraction(39, 40)) == 39.0
    assert quantile_type7(list(reversed(values)), Fraction(1, 40)) == pytest.approx(11.0)


def test_percentile_interval_and_invalid_inputs() -> None:
    assert percentile_ci95([]) is None
    assert percentile_ci95([0.5, 0.5]) == [0.5, 0.5]
    with pytest.raises(ValueError, match="at least one"):
        quantile_type7([], Fraction(1, 40))
    with pytest.raises(ValueError, match="Fraction"):
        quantile_type7([1.0], 0.025)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        quantile_type7([1.0, float("nan")], Fraction(1, 2))
    with pytest.raises(ValueError, match="finite"):
        quantile_type7([1.0, float("inf")], Fraction(1, 2))
    with pytest.raises(ValueError, match="finite"):
        quantile_type7([float("-inf"), 1.0], Fraction(1, 2))
