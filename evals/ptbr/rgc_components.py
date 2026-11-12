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
                {article_id for case_id in member_ids for article_id in citations_by_case[case_id]}
            )
        )
        canonical_json = json.dumps(list(article_ids), ensure_ascii=False, separators=(",", ":"))
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
    """DEC-021 two-sided sign-flip result with reproducibility metadata."""

    statistic_observed: int
    p_value_two_sided: float
    extreme_permutations: int
    permutations_considered: int
    minimum_resolution: float
    component_count: int
    significance_below_005_possible: bool
    method: str
    seed: int | None
    generator: str | None
    iterations: int


def exact_sign_flip(component_differences: Iterable[int]) -> SignFlipResult:
    """Run DEC-021 exactly for K <= 20 and with its fixed PCG64 for K > 20."""
    differences = tuple(component_differences)
    if not differences:
        raise ValueError("at least one component difference is required")
    if any(type(value) is not int for value in differences):
        raise ValueError("component differences must be integers")

    component_count = len(differences)
    observed = sum(differences)
    total = 1 << component_count
    minimum_resolution = 2 / total

    if component_count <= 20:
        extreme = 0
        for signs in product((-1, 1), repeat=component_count):
            permuted = sum(
                sign * difference for sign, difference in zip(signs, differences, strict=True)
            )
            if abs(permuted) >= abs(observed):
                extreme += 1
        return SignFlipResult(
            statistic_observed=observed,
            p_value_two_sided=extreme / total,
            extreme_permutations=extreme,
            permutations_considered=total,
            minimum_resolution=minimum_resolution,
            component_count=component_count,
            significance_below_005_possible=component_count >= 6,
            method="exact",
            seed=None,
            generator=None,
            iterations=0,
        )

    import numpy as np

    if np.__version__ != "2.3.3":
        raise RuntimeError(
            f"DEC-021 Monte Carlo requires numpy==2.3.3; found numpy=={np.__version__}"
        )
    seed = 20261003
    iterations = 10_000
    rng = np.random.Generator(np.random.PCG64(seed))
    extreme = 0
    values = np.asarray(differences, dtype=np.int64)
    for _ in range(iterations):
        signs = rng.choice([-1, +1], size=component_count, replace=True)
        permuted = int(np.sum(signs * values))
        if abs(permuted) >= abs(observed):
            extreme += 1

    return SignFlipResult(
        statistic_observed=observed,
        p_value_two_sided=(1 + extreme) / (1 + iterations),
        extreme_permutations=extreme,
        permutations_considered=iterations,
        minimum_resolution=minimum_resolution,
        component_count=component_count,
        significance_below_005_possible=component_count >= 6,
        method="monte_carlo",
        seed=seed,
        generator="numpy.random.Generator(numpy.random.PCG64)",
        iterations=iterations,
    )


class KappaBootstrapResult(NamedTuple):
    """DEC-022 component-bootstrap estimate and percentile interval."""

    kappa: float | None
    ci95: tuple[float, float] | None
    component_count: int
    case_count: int
    iterations: int
    seed: int
    generator: str
    valid_replicates: int
    undefined_replicates: int
    undefined_fraction: float
    rule_gap_excluded_count: int
    rule_gap_excluded_disagreements: int
    unstable: bool


def bootstrap_cohen_kappa_by_component(
    annotations_a: Mapping[str, str],
    annotations_b: Mapping[str, str],
    component_by_case: Mapping[str, str],
) -> KappaBootstrapResult:
    """Compute DEC-022 unweighted Cohen kappa and component percentile bootstrap.

    RULE_GAP pairs are excluded. Each bootstrap draw samples K components with
    replacement and carries every case in each selected component, preserving
    multiplicity. No case-level resampling or real annotation loading occurs.
    """
    vocabulary = (
        "SUPPORTED",
        "REFUTED",
        "UNVERIFIED",
        "PARTIALLY_SUPPORTED",
        "CONFLICTING",
    )
    allowed = set(vocabulary) | {"RULE_GAP"}
    ids = set(annotations_a)
    if ids != set(annotations_b) or ids != set(component_by_case):
        raise ValueError("annotation and component case IDs must match exactly")
    if not ids:
        raise ValueError("at least one annotated case is required")
    for name, labels in (("A", annotations_a), ("B", annotations_b)):
        invalid = sorted(
            (case_id, label)
            for case_id, label in labels.items()
            if not isinstance(label, str) or label not in allowed
        )
        if invalid:
            raise ValueError(f"annotator {name} has invalid labels: {invalid}")
    if any(
        not isinstance(component, str) or not component or component != component.strip()
        for component in component_by_case.values()
    ):
        raise ValueError("component IDs must be canonical non-empty strings")

    excluded = [
        case_id
        for case_id in sorted(ids)
        if annotations_a[case_id] == "RULE_GAP" or annotations_b[case_id] == "RULE_GAP"
    ]
    eligible = [case_id for case_id in sorted(ids) if case_id not in set(excluded)]
    if not eligible:
        raise ValueError("no eligible cases remain after excluding RULE_GAP pairs")

    groups: dict[str, list[str]] = {}
    for case_id in eligible:
        groups.setdefault(component_by_case[case_id], []).append(case_id)
    component_ids = sorted(groups)
    component_count = len(component_ids)

    def kappa_for(case_ids: list[str]) -> float | None:
        matrix = {a: {b: 0 for b in vocabulary} for a in vocabulary}
        for case_id in case_ids:
            matrix[annotations_a[case_id]][annotations_b[case_id]] += 1
        n = len(case_ids)
        observed = sum(matrix[label][label] for label in vocabulary) / n
        rows = {label: sum(matrix[label].values()) for label in vocabulary}
        columns = {label: sum(matrix[row][label] for row in vocabulary) for label in vocabulary}
        expected = sum(rows[label] * columns[label] for label in vocabulary) / (n * n)
        denominator = 1.0 - expected
        if abs(denominator) <= 1e-12:
            return None
        return (observed - expected) / denominator

    all_case_ids = [case_id for component in component_ids for case_id in groups[component]]
    point = kappa_for(all_case_ids)

    import numpy as np

    if np.__version__ != "2.3.3":
        raise RuntimeError(
            f"DEC-022 bootstrap requires numpy==2.3.3; found numpy=={np.__version__}"
        )
    seed = 20261003
    iterations = 10_000
    rng = np.random.Generator(np.random.PCG64(seed))
    bootstrap_values: list[float] = []
    undefined = 0
    for _ in range(iterations):
        selected = rng.integers(0, component_count, size=component_count)
        sampled_case_ids = [
            case_id
            for selected_index in selected
            for case_id in groups[component_ids[int(selected_index)]]
        ]
        value = kappa_for(sampled_case_ids)
        if value is None:
            undefined += 1
        else:
            bootstrap_values.append(value)

    ci95 = None
    if bootstrap_values:
        limits = np.quantile(bootstrap_values, (0.025, 0.975), method="linear")
        ci95 = (float(limits[0]), float(limits[1]))
    undefined_fraction = undefined / iterations
    return KappaBootstrapResult(
        kappa=point,
        ci95=ci95,
        component_count=component_count,
        case_count=len(eligible),
        iterations=iterations,
        seed=seed,
        generator="numpy.random.Generator(numpy.random.PCG64)",
        valid_replicates=len(bootstrap_values),
        undefined_replicates=undefined,
        undefined_fraction=undefined_fraction,
        rule_gap_excluded_count=len(excluded),
        rule_gap_excluded_disagreements=sum(
            annotations_a[case_id] != annotations_b[case_id] for case_id in excluded
        ),
        unstable=undefined_fraction > 0.05,
    )
