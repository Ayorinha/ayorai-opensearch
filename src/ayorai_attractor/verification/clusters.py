"""Deterministic evidence-cluster dependency rules from ADR-002/ADR-006."""

from collections.abc import Iterable

from .models import Evidence


def dependency_reason(left: Evidence, right: Evidence) -> str | None:
    """Return the first deterministic dependency rule that links two evidence items.

    A dependency means the two observations are not independent corroboration.
    Missing metadata is UNKNOWN; it never proves independence.
    """
    if left.canonical_url is not None and left.canonical_url == right.canonical_url:
        return "same_canonical_url"
    if left.origin_id is not None and left.origin_id == right.origin_id:
        return "same_origin_id"
    if left.source_id == right.source_id:
        return "same_source_id"
    if (
        left.normalized_content_hash is not None
        and left.normalized_content_hash == right.normalized_content_hash
    ):
        return "same_normalized_content_hash"
    if left.cited_origin_id is not None and right.origin_id is not None:
        if left.cited_origin_id == right.origin_id:
            return "citation_republication_chain"
    if right.cited_origin_id is not None and left.origin_id is not None:
        if right.cited_origin_id == left.origin_id:
            return "citation_republication_chain"
    return None


def has_known_dependency(left: Evidence, right: Evidence) -> bool:
    """Return whether ADR-002/ADR-006 establishes a dependency.

    Different domains, URLs or identifiers alone do not establish independence.
    """
    return left.id != right.id and dependency_reason(left, right) is not None


def cluster_evidence(items: Iterable[Evidence]) -> list[frozenset[str]]:
    """Build deterministic dependency clusters using transitive connectivity."""
    evidence = list(items)
    parent = {item.id: item.id for item in evidence}

    def find(item_id: str) -> str:
        while parent[item_id] != item_id:
            parent[item_id] = parent[parent[item_id]]
            item_id = parent[item_id]
        return item_id

    def union(left_id: str, right_id: str) -> None:
        left_root = find(left_id)
        right_root = find(right_id)
        if left_root != right_root:
            parent[right_root] = left_root

    for index, left in enumerate(evidence):
        for right in evidence[index + 1 :]:
            if has_known_dependency(left, right):
                union(left.id, right.id)

    clusters: dict[str, set[str]] = {}
    for item in evidence:
        clusters.setdefault(find(item.id), set()).add(item.id)

    return [frozenset(cluster) for cluster in clusters.values()]
