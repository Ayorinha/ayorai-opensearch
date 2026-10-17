"""ADR-010 phase 1 — Merkle core checked against an independent implementation.

Every expected value comes from the transparency-dev/merkle Go reference
(see ``vectors/README.md``); the Python code under test never generated it.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from ayorai_attractor.auditlog import merkle

VECTORS = json.loads(
    (Path(__file__).parent / "vectors" / "rfc6962-transparency-dev.json").read_text()
)
LEAVES = [bytes.fromhex(x) for x in VECTORS["leaves_hex"]]
LEAF_HASHES = [merkle.leaf_hash(x) for x in LEAVES]
ROOTS = [bytes.fromhex(x) for x in VECTORS["roots"]]
# Published constants of testonly.RootHashes() for sizes 0..8.
PUBLISHED_ROOT_8 = "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328"


def _hx(items: list[bytes]) -> list[str]:
    return [x.hex() for x in items]


def test_leaf_hashes_match_reference() -> None:
    assert _hx(LEAF_HASHES) == VECTORS["leaf_hashes"]


def test_empty_root_and_published_root() -> None:
    assert merkle.empty_root() == ROOTS[0]
    assert merkle.tree_root([]) == ROOTS[0]
    assert ROOTS[8].hex() == PUBLISHED_ROOT_8


@pytest.mark.parametrize("size", range(len(ROOTS)))
def test_tree_root_for_every_size(size: int) -> None:
    assert merkle.tree_root(LEAF_HASHES[:size]) == ROOTS[size]


@pytest.mark.parametrize(
    "vector", VECTORS["inclusion"], ids=lambda v: f"i{v['index']}-n{v['size']}"
)
def test_inclusion_proofs_match_and_verify(vector: dict[str, object]) -> None:
    index, size = int(vector["index"]), int(vector["size"])  # type: ignore[call-overload]
    expected = vector["proof"]
    proof = merkle.inclusion_proof(index, LEAF_HASHES[:size])
    assert _hx(proof) == expected
    assert merkle.verify_inclusion(index, size, LEAF_HASHES[index], proof, ROOTS[size])


@pytest.mark.parametrize(
    "vector", VECTORS["consistency"], ids=lambda v: f"c{v['size1']}-{v['size2']}"
)
def test_consistency_proofs_match_and_verify(vector: dict[str, object]) -> None:
    size1, size2 = int(vector["size1"]), int(vector["size2"])  # type: ignore[call-overload]
    proof = merkle.consistency_proof(size1, LEAF_HASHES[:size2])
    assert _hx(proof) == vector["proof"]
    assert merkle.verify_consistency(size1, size2, ROOTS[size1], ROOTS[size2], proof)


# ------------------------------------------------------------ mutation tests


def _flip(value: bytes, bit: int = 0) -> bytes:
    data = bytearray(value)
    data[bit // 8] ^= 1 << (bit % 8)
    return bytes(data)


def test_every_inclusion_mutation_is_rejected() -> None:
    rng = random.Random(20261017)  # nosec B311 - deterministic test sampling
    for vector in VECTORS["inclusion"]:
        index, size = vector["index"], vector["size"]
        proof = [bytes.fromhex(x) for x in vector["proof"]]
        leaf, root = LEAF_HASHES[index], ROOTS[size]
        assert not merkle.verify_inclusion(index, size, _flip(leaf), proof, root)
        assert not merkle.verify_inclusion(index, size, leaf, proof, _flip(root, 255))
        if proof:
            k = rng.randrange(len(proof))
            tampered = [*proof[:k], _flip(proof[k], rng.randrange(256)), *proof[k + 1 :]]
            assert not merkle.verify_inclusion(index, size, leaf, tampered, root)
            assert not merkle.verify_inclusion(index, size, leaf, proof[:-1], root)
            assert not merkle.verify_inclusion(index, size, leaf, list(reversed(proof)), root) or (
                proof == list(reversed(proof))
            )
        assert not merkle.verify_inclusion(index, size, leaf, [*proof, ROOTS[0]], root)
        if index + 1 < size:
            assert not merkle.verify_inclusion(index + 1, size, leaf, proof, root)
        # A proof for one tree head never verifies against a different head.
        if size + 1 < len(ROOTS):
            assert not merkle.verify_inclusion(index, size + 1, leaf, proof, ROOTS[size + 1])


def test_every_consistency_mutation_is_rejected() -> None:
    for vector in VECTORS["consistency"]:
        size1, size2 = vector["size1"], vector["size2"]
        proof = [bytes.fromhex(x) for x in vector["proof"]]
        root1, root2 = ROOTS[size1], ROOTS[size2]
        assert not merkle.verify_consistency(size1, size2, _flip(root1), root2, proof)
        assert not merkle.verify_consistency(size1, size2, root1, _flip(root2), proof)
        for k in range(len(proof)):
            tampered = [*proof[:k], _flip(proof[k], 7), *proof[k + 1 :]]
            assert not merkle.verify_consistency(size1, size2, root1, root2, tampered)
        if proof:
            assert not merkle.verify_consistency(size1, size2, root1, root2, proof[:-1])
        assert not merkle.verify_consistency(size1, size2, root1, root2, [*proof, ROOTS[0]])
        if size2 + 1 < len(ROOTS):
            assert not merkle.verify_consistency(size1, size2 + 1, root1, ROOTS[size2 + 1], proof)


def test_rewritten_history_is_not_consistent() -> None:
    """A log that replaced leaf 3 cannot prove consistency with its old head."""
    rewritten = list(LEAF_HASHES)
    rewritten[3] = merkle.leaf_hash(b"rewritten")
    proof = merkle.consistency_proof(5, rewritten[:12])
    assert not merkle.verify_consistency(5, 12, ROOTS[5], merkle.tree_root(rewritten[:12]), proof)


def test_reordered_leaves_change_the_root() -> None:
    swapped = list(LEAF_HASHES[:9])
    swapped[1], swapped[2] = swapped[2], swapped[1]
    assert merkle.tree_root(swapped) != ROOTS[9]


def test_truncated_log_fails_inclusion_of_a_dropped_leaf() -> None:
    proof = merkle.inclusion_proof(10, LEAF_HASHES[:12])
    assert not merkle.verify_inclusion(10, 12, LEAF_HASHES[10], proof, ROOTS[10])


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((0, 0, b"\x00" * 32, b"\x00" * 32, []), False),  # empty first tree
        ((3, 2, ROOTS[3], ROOTS[2], []), False),  # shrinking
        ((4, 4, ROOTS[4], ROOTS[4], []), True),
        ((4, 4, ROOTS[4], ROOTS[4], [ROOTS[1]]), False),
        ((2, 5, ROOTS[2], ROOTS[5], []), False),  # empty proof
        ((2, 5, b"short", ROOTS[5], [ROOTS[1]]), False),
        ((2, 5, ROOTS[2], ROOTS[5], [b"short"]), False),
    ],
)
def test_consistency_edge_cases(args: tuple[object, ...], expected: bool) -> None:
    assert merkle.verify_consistency(*args) is expected  # type: ignore[arg-type]


def test_inclusion_edge_cases_never_raise() -> None:
    leaf = LEAF_HASHES[0]
    assert not merkle.verify_inclusion(0, 0, leaf, [], ROOTS[0])
    assert not merkle.verify_inclusion(-1, 3, leaf, [], ROOTS[3])
    assert not merkle.verify_inclusion(0, 1, b"short", [], ROOTS[1])
    assert not merkle.verify_inclusion(0, 2, leaf, [b"short"], ROOTS[2])
    assert merkle.verify_inclusion(0, 1, leaf, [], ROOTS[1])
    with pytest.raises(ValueError):
        merkle.inclusion_proof(3, LEAF_HASHES[:3])
    with pytest.raises(ValueError):
        merkle.consistency_proof(0, LEAF_HASHES[:3])
    with pytest.raises(ValueError):
        merkle.tree_root([b"short"])


# Published constants of transparency-dev/merkle testonly.RootHashes(), commit
# c39fbf350a405f68571bf4c42a6a518eb0a46a4b, copied verbatim for sizes 0..8.
PUBLISHED_ROOTS = [
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
    "fac54203e7cc696cf0dfcb42c92a1d9dbaf70ad9e621f4bd8d98662f00e3c125",
    "aeb6bcfe274b70a14fb067a5e5578264db0fa9b51af5e0ba159158f329e06e77",
    "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
    "4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4",
    "76e67dadbcdf1e10e1b74ddc608abd2f98dfb16fbce75277b5232a127f2087ef",
    "ddb89be403809e325750d3d263cd78929c2942b7942a34b77e122c9594a74c8c",
    "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328",
]


@pytest.mark.parametrize("size", range(len(PUBLISHED_ROOTS)))
def test_each_published_root_matches(size: int) -> None:
    assert merkle.tree_root(LEAF_HASHES[:size]).hex() == PUBLISHED_ROOTS[size]


MALFORMED_PROOFS: list[object] = [None, 42, "abc", b"x" * 32, {"a": 1}, iter([]), [None]]
NON_INTEGERS: list[object] = [True, False, None, 1.0, "1"]


@pytest.mark.parametrize("proof", MALFORMED_PROOFS, ids=repr)
def test_malformed_proof_objects_return_false(proof: object) -> None:
    leaf = LEAF_HASHES[0]
    assert merkle.verify_inclusion(0, 2, leaf, proof, ROOTS[2]) is False  # type: ignore[arg-type]
    assert merkle.verify_consistency(2, 3, ROOTS[2], ROOTS[3], proof) is False  # type: ignore[arg-type]


@pytest.mark.parametrize("value", NON_INTEGERS, ids=repr)
def test_booleans_and_non_integers_are_not_sizes_or_indices(value: object) -> None:
    leaf, proof1 = LEAF_HASHES[1], merkle.inclusion_proof(1, LEAF_HASHES[:2])
    # True == 1 in Python; without the explicit check this call would verify.
    assert merkle.verify_inclusion(value, 2, leaf, proof1, ROOTS[2]) is False  # type: ignore[arg-type]
    assert merkle.verify_inclusion(1, value, leaf, proof1, ROOTS[2]) is False  # type: ignore[arg-type]
    proof = merkle.consistency_proof(1, LEAF_HASHES[:2])
    assert merkle.verify_consistency(value, 2, ROOTS[1], ROOTS[2], proof) is False  # type: ignore[arg-type]
    assert merkle.verify_consistency(1, value, ROOTS[1], ROOTS[2], proof) is False  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        merkle.inclusion_proof(value, LEAF_HASHES[:2])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        merkle.consistency_proof(value, LEAF_HASHES[:2])  # type: ignore[arg-type]


def test_tuple_proofs_are_accepted() -> None:
    proof = tuple(merkle.inclusion_proof(3, LEAF_HASHES[:7]))
    assert merkle.verify_inclusion(3, 7, LEAF_HASHES[3], proof, ROOTS[7])
