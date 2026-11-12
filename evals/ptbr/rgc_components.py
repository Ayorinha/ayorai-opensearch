"""Deterministic connected components for RGC article-citation clusters.

This module is deliberately pure: it does not load benchmark files, invoke the
ATTRACTOR/Judge, or perform statistical inference. Callers must provide the
case records explicitly. It implements the graph unit specified by DEC-023.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping
from itertools import product
from typing import NamedTuple


class ArticleComponent(NamedTuple):
    """One connected component of cases linked by shared cited article IDs."""

    component_id: str
    case_ids: tuple[str, ...]
    article_ids: tuple[str, ...]
    canonical_article_ids_json: str


class ComponentSummary(NamedTuple):
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
    unique, trimmed, NFC-normalized article IDs. Component IDs are SHA-256
    commitments to the canonical compact JSON array required by DEC-023.
    No input is modified.
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
                or article_id != unicodedata.normalize("NFC", article_id)
            ):
                raise ValueError(f"{case_id}: article IDs must be canonical non-empty NFC strings")
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
        canonical_json = json.dumps(
            list(article_ids), ensure_ascii=False, separators=(",", ":")
        )
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        component_id = f"component:sha256:{digest}"
        components.append(
            ArticleComponent(
                component_id=component_id,
                case_ids=member_ids,
                article_ids=article_ids,
                canonical_article_ids_json=canonical_json,
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


class SignFlipResult(NamedTuple):
    """Exact two-sided sign-flip result for at most 20 independent components."""

    statistic_observed: int
    p_value_two_sided: float
    extreme_permutations: int
    permutations_considered: int
    minimum_resolution: float
    component_count: int
    significance_below_005_possible: bool


def exact_sign_flip(component_differences: Iterable[int]) -> SignFlipResult:
    """Enumerate the DEC-021 sign space exactly when K <= 20.

    Monte Carlo mode for K > 20 is intentionally not guessed here: the
    repository's decision record must settle the exact PRNG/version before
    that path can claim deterministic reproducibility.
    """
    differences = tuple(component_differences)
    if not differences:
        raise ValueError("at least one component difference is required")
    if any(type(value) is not int for value in differences):
        raise ValueError("component differences must be integers")
    component_count = len(differences)
    if component_count > 20:
        raise ValueError("K > 20 requires the maintainer-approved deterministic PRNG specification")

    observed = sum(differences)
    total = 1 << component_count
    extreme = 0
    for signs in product((-1, 1), repeat=component_count):
        permuted = sum(
            sign * difference
            for sign, difference in zip(signs, differences, strict=True)
        )
        if abs(permuted) >= abs(observed):
            extreme += 1

    return SignFlipResult(
        statistic_observed=observed,
        p_value_two_sided=extreme / total,
        extreme_permutations=extreme,
        permutations_considered=total,
        minimum_resolution=2 / total,
        component_count=component_count,
        significance_below_005_possible=2 / total < 0.05,
    )
