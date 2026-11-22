"""Boundary validation for the incremental Merkle tree used by P2."""

import pytest

from ayorai_attractor.auditlog.merkle import IncrementalTree


@pytest.mark.parametrize("leaf", [b"", b"x", bytes(31), bytes(33), None])
def test_incremental_tree_rejects_non_sha256_leaf_hashes(leaf: object) -> None:
    tree = IncrementalTree()
    with pytest.raises(ValueError, match="32 bytes"):
        tree.append(leaf)  # type: ignore[arg-type]
