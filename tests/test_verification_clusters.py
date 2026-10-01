from datetime import UTC, datetime

from hypothesis import given, strategies as st

from ayorai_attractor.verification.clusters import (
    are_independent,
    cluster_evidence,
    dependency_reason,
)
from ayorai_attractor.verification.models import Evidence


def evidence(
    item_id: str,
    *,
    canonical_url: str | None = "https://example.test/a",
    origin_id: str | None = None,
    normalized_content_hash: str | None = None,
    cited_origin_id: str | None = None,
) -> Evidence:
    return Evidence(
        id=item_id,
        claim_id="c1",
        source_id=item_id,
        source_location=canonical_url or "https://example.test/doc",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        start_offset=0,
        end_offset=10,
        excerpt="evidence",
        origin_id=origin_id,
        canonical_url=canonical_url,
        normalized_content_hash=normalized_content_hash,
        cited_origin_id=cited_origin_id,
    )


def test_same_canonical_url_is_dependent() -> None:
    left = evidence("e1", canonical_url="https://example.test/a")
    right = evidence("e2", canonical_url="https://example.test/a")
    assert dependency_reason(left, right) == "same_canonical_url"
    assert not are_independent(left, right)


def test_same_origin_is_dependent_across_domains() -> None:
    left = evidence("e1", canonical_url="https://one.test/a", origin_id="o1")
    right = evidence("e2", canonical_url="https://two.test/a", origin_id="o1")
    assert dependency_reason(left, right) == "same_origin_id"
    assert not are_independent(left, right)


def test_same_normalized_hash_is_dependent() -> None:
    left = evidence("e1", canonical_url="https://one.test/a", normalized_content_hash="h1")
    right = evidence("e2", canonical_url="https://two.test/a", normalized_content_hash="h1")
    assert dependency_reason(left, right) == "same_normalized_content_hash"


def test_citation_republication_chain_is_dependent() -> None:
    left = evidence("e1", origin_id="o1")
    right = evidence("e2", origin_id="o2", cited_origin_id="o1")
    assert dependency_reason(left, right) == "citation_republication_chain"


def test_different_domains_alone_do_not_prove_independence() -> None:
    left = evidence("e1", canonical_url="https://one.test/a", origin_id=None)
    right = evidence("e2", canonical_url="https://two.test/a", origin_id=None)
    assert are_independent(left, right)


@given(st.text(min_size=1), st.text(min_size=1))
def test_disjoint_origin_ids_are_independent(left_origin: str, right_origin: str) -> None:
    if left_origin == right_origin:
        return
    left = evidence("e1", origin_id=left_origin)
    right = evidence("e2", origin_id=right_origin)
    assert are_independent(left, right)


def test_clusters_are_transitively_closed() -> None:
    first = evidence("e1", origin_id="o1")
    middle = evidence("e2", origin_id="o1", canonical_url="https://two.test/m")
    last = evidence("e3", origin_id="o3", cited_origin_id="o1")

    clusters = cluster_evidence([first, middle, last])
    assert frozenset({"e1", "e2", "e3"}) in clusters
