"""Deterministic connected components for RGC article-citation clusters.

This module is deliberately pure: it does not load benchmark files, invoke the
ATTRACTOR/Judge, or perform statistical inference. Callers must provide the
case records explicitly. It implements the graph unit specified by DEC-023.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArticleComponent:
    """One connected component of cases linked by shared cited article IDs."""

    component_id: str
    case_ids: tuple[str, ...]
    article_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComponentSummary:
    """Deterministic component inventory suitable for audit reports."""

    components: tuple[ArticleComponent, ...]
    original_cluster_count: int
    component_count: int
    case_count: int
    largest_component_size: int
    component_sizes: tuple[int, ...]


class _DisjointSet:
    """Union-find with path compression and union by size."""

    def __init__(self, values: Iterable[str]) -> None:
        self.parent = {value: value for value in values}
        self.size = dict.fromkeys(self.parent, 1)

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.size[root_left] < self.size[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        self.size[root_left] += self.size[root_right]


def build_article_components(
    cases: Iterable[Mapping[str, object]],
) -> ComponentSummary:
    """Build transitive case components from complete cited_article_ids lists.

    Every case must have a unique non-empty case_id and a non-empty list of
    unique, trimmed article IDs. The '+' delimiter is reserved by DEC-023's
    canonical component ID representation and is rejected inside IDs to avoid
    ambiguous serialization. No input is modified.
    """
    records = list(cases)
    case_ids: list[str] = []
    citations_by_case: dict[str, tuple[str, ...]] = {}
    original_clusters: set[str] = set()

    for index, case in enumerate(records):
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id != case_id.strip():
            raise ValueError(f"case at index {index}: case_id must be a canonical non-empty string")
        if case_id in citations_by_case:
            raise ValueError(f"duplicate case_id {case_id!r}")

        raw_citations = case.get("cited_article_ids")
        if not isinstance(raw_citations, list) or not raw_citations:
            raise ValueError(f"{case_id}: cited_article_ids must be a non-empty list")

        citations: list[str] = []
        seen: set[str] = set()
        for article_id in raw_citations:
            if (
                not isinstance(article_id, str)
                or not article_id
                or article_id != article_id.strip()
            ):
                raise ValueError(
                    f"{case_id}: article IDs must be canonical non-empty strings"
                )
            if "+" in article_id:
                raise ValueError(
                    f"{case_id}: article ID {article_id!r} contains reserved '+' delimiter"
                )
            if article_id in seen:
                raise ValueError(f"{case_id}: duplicate article ID {article_id!r}")
            seen.add(article_id)
            citations.append(article_id)

        case_ids.append(case_id)
        citations_by_case[case_id] = tuple(citations)

        cluster_id = case.get("bootstrap_cluster_id")
        if isinstance(cluster_id, str) and cluster_id:
            original_clusters.add(cluster_id)

    disjoint = _DisjointSet(case_ids)
    first_case_by_article: dict[str, str] = {}
    for case_id in case_ids:
        for article_id in citations_by_case[case_id]:
            previous = first_case_by_article.setdefault(article_id, case_id)
            disjoint.union(case_id, previous)

    grouped_cases: dict[str, list[str]] = {}
    for case_id in case_ids:
        grouped_cases.setdefault(disjoint.find(case_id), []).append(case_id)

    components: list[ArticleComponent] = []
    for members in grouped_cases.values():
        member_ids = tuple(sorted(members))
        article_ids = tuple(
            sorted(
                {
                    article_id
                    for case_id in member_ids
                    for article_id in citations_by_case[case_id]
                }
            )
        )
        component_id = "component:" + "+".join(article_ids)
        components.append(
            ArticleComponent(
                component_id=component_id,
                case_ids=member_ids,
                article_ids=article_ids,
            )
        )

    components.sort(key=lambda component: component.component_id)
    sizes = tuple(sorted((len(component.case_ids) for component in components), reverse=True))
    return ComponentSummary(
        components=tuple(components),
        original_cluster_count=len(original_clusters),
        component_count=len(components),
        case_count=len(case_ids),
        largest_component_size=sizes[0] if sizes else 0,
        component_sizes=sizes,
    )
