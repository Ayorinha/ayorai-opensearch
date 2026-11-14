"""Deterministic connected components for RGC article-citation clusters.

This module is deliberately pure: it does not load benchmark files, invoke the
ATTRACTOR/Judge, or perform statistical inference. Callers must provide the
case records explicitly. It implements the graph unit specified by DEC-023.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from itertools import product
from typing import NamedTuple

from evals.ptbr.rgc_ids import (
    cluster_members,
    component_id,
    parse_component_id,
    require_article_id,
)
from evals.ptbr.rgc_random import (
    LABEL_COMPONENT_KAPPA,
    LABEL_SIGN_FLIP,
    RGC_SEED,
    RgcPrng,
    percentile_ci95,
)


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
    unique canonical article IDs and a valid original bootstrap_cluster_id.
    Component IDs use the literal DEC-023 representation from rgc_ids.
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
            article_id = require_article_id(article_id, f"{case_id}: cited_article_ids")
            if article_id in seen:
                raise ValueError(f"{case_id}: duplicate article ID {article_id!r}")
            seen.add(article_id)
            citations.append(article_id)

        case_ids.append(case_id)
        citations_by_case[case_id] = tuple(citations)

        cluster_id = case.get("bootstrap_cluster_id")
        if not isinstance(cluster_id, str):
            raise ValueError(f"{case_id}: bootstrap_cluster_id must be a string")
        cluster_members(cluster_id, f"{case_id}: bootstrap_cluster_id")
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
        canonical_id = component_id(article_ids, where="connected component")
        components.append(
            ArticleComponent(
                component_id=canonical_id,
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
    """DEC-021 two-sided sign-flip result with reproducibility metadata.

    ``component_ids`` is the order in which components were consumed (lexical order of
    their canonical IDs), so a Monte Carlo result can be reproduced from the report.
    ``theoretical_exact_resolution`` is DEC-021's minimum attainable two-sided p of the
    exact test, 2 / 2**K; ``monte_carlo_minimum_p`` is the smallest p the Monte Carlo
    estimator can return, 1 / (1 + iterations), and is None for the exact test.
    """

    statistic_observed: int
    p_value_two_sided: float
    extreme_permutations: int
    permutations_considered: int
    theoretical_exact_resolution: float
    monte_carlo_minimum_p: float | None
    component_count: int
    component_ids: tuple[str, ...]
    significance_below_005_possible: bool
    method: str
    seed: int | None
    generator: str | None
    iterations: int


def _ordered_differences(
    component_differences: Mapping[str, int],
) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """Components in lexical order of their canonical IDs, whatever the input order."""

    if not isinstance(component_differences, Mapping):
        raise TypeError("component differences must map component IDs to integers")
    if not component_differences:
        raise ValueError("at least one component difference is required")
    for component_identifier, value in component_differences.items():
        parse_component_id(component_identifier, "sign-flip component ID")
        if type(value) is not int:
            raise ValueError("component differences must be integers")
    component_ids = tuple(sorted(component_differences))
    return component_ids, tuple(component_differences[cid] for cid in component_ids)


def sign_flip_by_component(component_differences: Mapping[str, int]) -> SignFlipResult:
    """Run DEC-021 exactly for K <= 20 and with RGC-PRNG-1 for K > 20.

    The input maps each component ID to its paired difference a_k - b_k. Components are
    consumed in lexical order of their IDs, so the result does not depend on the order
    in which the caller built the mapping.
    """
    component_ids, differences = _ordered_differences(component_differences)

    component_count = len(differences)
    observed = sum(differences)
    total = 1 << component_count
    theoretical_exact_resolution = 2 / total

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
            theoretical_exact_resolution=theoretical_exact_resolution,
            monte_carlo_minimum_p=None,
            component_count=component_count,
            component_ids=component_ids,
            significance_below_005_possible=component_count >= 6,
            method="exact",
            seed=None,
            generator=None,
            iterations=0,
        )

    seed = RGC_SEED
    iterations = 10_000
    rng = RgcPrng(seed, LABEL_SIGN_FLIP)
    extreme = 0
    for _ in range(iterations):
        permuted = sum(rng.sign() * difference for difference in differences)
        if abs(permuted) >= abs(observed):
            extreme += 1

    return SignFlipResult(
        statistic_observed=observed,
        p_value_two_sided=(1 + extreme) / (1 + iterations),
        extreme_permutations=extreme,
        permutations_considered=iterations,
        theoretical_exact_resolution=theoretical_exact_resolution,
        monte_carlo_minimum_p=1 / (1 + iterations),
        component_count=component_count,
        component_ids=component_ids,
        significance_below_005_possible=component_count >= 6,
        method="monte_carlo",
        seed=seed,
        generator="RGC-PRNG-1",
        iterations=iterations,
    )


class KappaBootstrapResult(NamedTuple):
    """DEC-022 component-bootstrap estimate and percentile interval."""

    kappa: float | None
    ci95: tuple[float, float] | None
    component_count: int
    case_count: int
    method: str
    iterations: int
    seed: int
    generator: str
    percentile: str
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
    for component in component_by_case.values():
        parse_component_id(component, "kappa component ID")

    excluded = [
        case_id
        for case_id in sorted(ids)
        if annotations_a[case_id] == "RULE_GAP" or annotations_b[case_id] == "RULE_GAP"
    ]
    excluded_set = set(excluded)
    eligible = [case_id for case_id in sorted(ids) if case_id not in excluded_set]
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

    seed = RGC_SEED
    iterations = 10_000
    rng = RgcPrng(seed, LABEL_COMPONENT_KAPPA)
    bootstrap_values: list[float] = []
    undefined = 0
    for _ in range(iterations):
        selected = [rng.below(component_count) for _ in range(component_count)]
        sampled_case_ids = [
            case_id
            for selected_index in selected
            for case_id in groups[component_ids[selected_index]]
        ]
        value = kappa_for(sampled_case_ids)
        if value is None:
            undefined += 1
        else:
            bootstrap_values.append(value)

    limits = percentile_ci95(bootstrap_values)
    ci95 = None if limits is None else (limits[0], limits[1])
    undefined_fraction = undefined / iterations
    return KappaBootstrapResult(
        kappa=point,
        ci95=ci95,
        component_count=component_count,
        case_count=len(eligible),
        method="percentile_component_bootstrap",
        iterations=iterations,
        seed=seed,
        generator="RGC-PRNG-1",
        percentile="hyndman-fan-type-7",
        valid_replicates=len(bootstrap_values),
        undefined_replicates=undefined,
        undefined_fraction=undefined_fraction,
        rule_gap_excluded_count=len(excluded),
        rule_gap_excluded_disagreements=sum(
            annotations_a[case_id] != annotations_b[case_id] for case_id in excluded
        ),
        unstable=undefined_fraction > 0.05,
    )
