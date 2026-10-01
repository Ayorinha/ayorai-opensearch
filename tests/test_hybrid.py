import pytest

from ayorai_attractor.hybrid import RankedHit, rrf_fuse


def test_rrf_fuses_two_rankings_deterministically() -> None:
    result = rrf_fuse(
        [RankedHit("a", 10), RankedHit("b", 9)],
        [RankedHit("b", 10), RankedHit("c", 9)],
    )
    assert [item.document_id for item in result] == ["b", "a", "c"]
    assert result[0].score > result[1].score


def test_rrf_rejects_zero_total_weight() -> None:
    with pytest.raises(ValueError):
        rrf_fuse([], [], lexical_weight=0, semantic_weight=0)
