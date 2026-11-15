"""Synthetic tests for DEC-023 connected article components."""

from __future__ import annotations

import json
import runpy
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_components.py"))


def _build_article_components(cases: list[dict[str, object]]) -> Any:
    prepared = []
    for index, case in enumerate(cases):
        record = dict(case)
        record.setdefault("bootstrap_cluster_id", f"synthetic-cluster-{index}")
        prepared.append(record)
    return MODULE["build_article_components"](prepared)


def test_connected_inventory_uses_only_case_ids_and_citations() -> None:
    cases = [
        {"case_id": "case-a", "cited_article_ids": ["article:one"]},
        {"case_id": "case-b", "cited_article_ids": ["article:one", "article:two"]},
        {"case_id": "case-c", "cited_article_ids": ["article:three"]},
    ]

    components = MODULE["build_connected_article_components"](cases)

    assert len(components) == 2
    assert components[0].component_id == "component:article:one+article:two"
    assert components[0].case_ids == ("case-a", "case-b")
    assert components[1].component_id == "component:article:three"
    assert components[1].case_ids == ("case-c",)


def test_components_merge_transitively_and_keep_isolated_cases() -> None:
    cases = [
        {"case_id": "case-a", "cited_article_ids": ["art-1"], "bootstrap_cluster_id": "old-1"},
        {
            "case_id": "case-b",
            "cited_article_ids": ["art-1", "art-2"],
            "bootstrap_cluster_id": "old-2",
        },
        {"case_id": "case-c", "cited_article_ids": ["art-2"], "bootstrap_cluster_id": "old-3"},
        {"case_id": "case-d", "cited_article_ids": ["art-9"], "bootstrap_cluster_id": "old-4"},
    ]

    result = MODULE["build_article_components"](cases)

    assert result.original_cluster_count == 4
    assert result.component_count == 2
    assert result.case_count == 4
    assert result.largest_component_size == 3
    assert result.component_sizes == (3, 1)
    expected_json = json.dumps(["art-1", "art-2"], ensure_ascii=False, separators=(",", ":"))
    assert result.components[0].component_id == "component:art-1+art-2"
    assert result.components[0].canonical_article_ids_json == expected_json
    assert result.components[0].case_ids == ("case-a", "case-b", "case-c")
    assert result.components[1].article_ids == ("art-9",)
    assert result.components[1].canonical_article_ids_json == '["art-9"]'
    assert result.components[1].component_id == "component:art-9"


def test_component_output_is_independent_of_input_order() -> None:
    cases = [
        {"case_id": "b", "cited_article_ids": ["z", "x"]},
        {"case_id": "a", "cited_article_ids": ["x"]},
        {"case_id": "c", "cited_article_ids": ["q"]},
    ]

    forward = _build_article_components(cases)
    reverse = _build_article_components(list(reversed(cases)))

    assert forward == reverse


def test_shared_article_joins_multiple_cases_even_with_different_old_clusters() -> None:
    cases = [
        {"case_id": "a", "cited_article_ids": ["shared"], "bootstrap_cluster_id": "cluster-a"},
        {"case_id": "b", "cited_article_ids": ["shared"], "bootstrap_cluster_id": "cluster-b"},
    ]

    result = MODULE["build_article_components"](cases)

    assert result.original_cluster_count == 2
    assert result.component_count == 1
    assert result.components[0].case_ids == ("a", "b")


@pytest.mark.parametrize(
    "cases, message",
    [
        ([{"case_id": "a", "cited_article_ids": []}], "non-empty list"),
        ([{"case_id": "a", "cited_article_ids": ["x", "x"]}], "duplicate article ID"),
        ([{"case_id": "a", "cited_article_ids": [" x"]}], "canonical"),
        (
            [
                {"case_id": "a", "cited_article_ids": ["x"]},
                {"case_id": "a", "cited_article_ids": ["y"]},
            ],
            "duplicate case_id",
        ),
    ],
)
def test_invalid_component_inputs_fail_closed(cases: list[dict[str, object]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _build_article_components(cases)


def test_plus_is_rejected_inside_article_ids() -> None:
    with pytest.raises(ValueError, match="canonical article ID"):
        _build_article_components([{"case_id": "a", "cited_article_ids": ["x+y"]}])


def test_non_ascii_article_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="canonical article ID"):
        _build_article_components([{"case_id": "a", "cited_article_ids": ["ação"]}])


@pytest.mark.parametrize("cluster_id", [None, "", 7, "bundle:bad+bad"])
def test_invalid_original_cluster_id_fails_closed(cluster_id: object) -> None:
    with pytest.raises(ValueError):
        MODULE["build_article_components"](
            [
                {
                    "case_id": "a",
                    "cited_article_ids": ["article:a"],
                    "bootstrap_cluster_id": cluster_id,
                }
            ]
        )


def test_missing_original_cluster_id_fails_closed() -> None:
    with pytest.raises(ValueError):
        MODULE["build_article_components"]([{"case_id": "a", "cited_article_ids": ["article:a"]}])


def test_empty_input_has_a_well_formed_empty_summary() -> None:
    result = MODULE["build_article_components"]([])

    assert result.components == ()
    assert result.component_count == 0
    assert result.case_count == 0
    assert result.largest_component_size == 0
    assert result.component_sizes == ()


def _components(*differences: int) -> dict[str, int]:
    return {f"component:syn-{index:02d}": value for index, value in enumerate(differences)}


def _brute_force_p(differences: list[int]) -> float:
    """Independent reference: enumerate every sign vector, two-sided, |T*| >= |T_obs|."""

    observed = abs(sum(differences))
    hits = 0
    for mask in range(1 << len(differences)):
        total = sum(-d if (mask >> i) & 1 else d for i, d in enumerate(differences))
        hits += abs(total) >= observed
    return hits / (1 << len(differences))


def test_sign_flip_by_component_enumerates_all_sign_combinations() -> None:
    result = MODULE["sign_flip_by_component"](_components(1, 1))

    assert result.statistic_observed == 2
    assert result.permutations_considered == 4
    assert result.extreme_permutations == 2
    assert result.p_value_two_sided == 0.5
    assert result.theoretical_exact_resolution == 0.5
    assert result.monte_carlo_minimum_p is None
    assert result.significance_below_005_possible is False


def test_sign_flip_by_component_keeps_zero_difference_components() -> None:
    result = MODULE["sign_flip_by_component"](_components(1, 0))

    assert result.component_count == 2
    assert result.permutations_considered == 4
    assert result.p_value_two_sided == 1.0


def test_zero_difference_components_do_not_count_toward_attainable_significance() -> None:
    # K = 6, but one component has d_k = 0: every sign vector of the five informative
    # components appears twice, so the smallest attainable p is 2 / 2^5 = 0.0625.
    result = MODULE["sign_flip_by_component"](_components(1, 1, 1, 1, 1, 0))

    assert result.component_count == 6
    assert result.informative_component_count == 5
    assert result.p_value_two_sided == result.minimum_attainable_p == 2 / 2**5
    assert result.theoretical_exact_resolution == 2 / 2**6
    assert result.significance_below_005_possible is False

    six = MODULE["sign_flip_by_component"](_components(1, 1, 1, 1, 1, 1, 0))
    assert six.informative_component_count == 6
    assert six.p_value_two_sided == six.minimum_attainable_p == 2 / 2**6
    assert six.significance_below_005_possible is True


@pytest.mark.parametrize(
    "differences",
    [[0], [0, 0, 0], [2, -1, 0, 3], [1, 1, 1, 1, 1, 1], [3, 0, -2, 0, 1, 1, 0, 2]],
)
def test_minimum_attainable_p_is_the_smallest_p_of_the_exact_null(differences: list[int]) -> None:
    from itertools import product

    result = MODULE["sign_flip_by_component"](_components(*differences))
    totals = [
        abs(sum(s * d for s, d in zip(signs, differences, strict=True)))
        for signs in product((-1, 1), repeat=len(differences))
    ]
    smallest = sum(t >= max(totals) for t in totals) / len(totals)
    assert result.minimum_attainable_p == smallest
    assert result.significance_below_005_possible is (smallest < 0.05)


def test_monte_carlo_attainable_significance_uses_informative_components() -> None:
    result = MODULE["sign_flip_by_component"](_components(*([1] * 5 + [0] * 20)))

    assert result.method == "monte_carlo"
    assert (result.component_count, result.informative_component_count) == (25, 5)
    assert result.minimum_attainable_p == 2 / 2**5
    assert result.significance_below_005_possible is False


def test_sign_flip_by_component_is_symmetric_and_deterministic() -> None:
    fn = MODULE["sign_flip_by_component"]
    positive = fn(_components(3, -2, 1))
    negative = fn(_components(-3, 2, -1))

    assert positive.statistic_observed == -negative.statistic_observed
    assert positive.p_value_two_sided == negative.p_value_two_sided
    assert positive.extreme_permutations == negative.extreme_permutations
    assert positive.permutations_considered == negative.permutations_considered


@pytest.mark.parametrize(
    "differences",
    [
        [2, -1, 0, 3],
        [1, 1, 1, 1, 1, 1],
        [5, -4, 3, -2, 1, 0, 2],
        [0, 0, 0],
        [7, -7, 1, 2, -3, 4, 1, -1],
    ],
)
def test_sign_flip_by_component_matches_independent_enumeration(differences: list[int]) -> None:
    result = MODULE["sign_flip_by_component"](_components(*differences))

    assert result.method == "exact"
    assert result.p_value_two_sided == _brute_force_p(differences)
    assert result.theoretical_exact_resolution == 2 / 2 ** len(differences)


def test_sign_flip_by_component_is_exact_up_to_k_20() -> None:
    differences = [1, -1] * 9 + [3, 2]  # K = 20
    result = MODULE["sign_flip_by_component"](_components(*differences))

    assert result.method == "exact"
    assert result.component_count == 20
    assert result.permutations_considered == 2**20
    assert result.theoretical_exact_resolution == 2 / 2**20
    assert result.monte_carlo_minimum_p is None


def test_sign_flip_by_component_does_not_depend_on_input_order() -> None:
    fn = MODULE["sign_flip_by_component"]
    items = list(_components(4, -1, 2, 0, -3, 5, 1).items())
    forward = fn(dict(items))
    backward = fn(dict(reversed(items)))
    shuffled = fn(dict(items[3:] + items[:3]))

    assert forward == backward == shuffled
    assert forward.component_ids == tuple(sorted(key for key, _ in items))


def test_monte_carlo_sign_flip_does_not_depend_on_input_order_k_25() -> None:
    fn = MODULE["sign_flip_by_component"]
    differences = [((index * 7) % 5) - 2 for index in range(25)]  # K = 25, mixed signs
    items = list(_components(*differences).items())
    forward = fn(dict(items))
    backward = fn(dict(reversed(items)))
    rotated = fn(dict(items[11:] + items[:11]))

    assert forward.method == "monte_carlo"
    assert forward.component_count == 25
    assert forward == backward == rotated
    assert forward.component_ids == tuple(sorted(key for key, _ in items))
    assert forward.p_value_two_sided == (1 + forward.extreme_permutations) / 10_001
    assert forward.theoretical_exact_resolution == 2 / 2**25
    assert forward.monte_carlo_minimum_p == 1 / 10_001
    assert forward.monte_carlo_minimum_p <= forward.p_value_two_sided <= 1


def test_sign_flip_by_component_rejects_invalid_inputs() -> None:
    fn = MODULE["sign_flip_by_component"]
    with pytest.raises(ValueError, match="at least one"):
        fn({})
    with pytest.raises(ValueError, match="integers"):
        fn({"component:a": 1, "component:b": True})
    with pytest.raises(ValueError, match="component:"):
        fn({" component:a": 1})
    with pytest.raises(TypeError, match="map component IDs"):
        fn([1, 2])


def test_monte_carlo_sign_flip_uses_rgc_prng_1() -> None:
    fn = MODULE["sign_flip_by_component"]
    first = fn(_components(*([1] * 21)))
    second = fn(_components(*([1] * 21)))

    assert first == second
    assert first.method == "monte_carlo"
    assert first.seed == 20261003
    assert first.generator == "RGC-PRNG-1"
    assert first.iterations == 10_000
    assert first.theoretical_exact_resolution == 2 / (2**21)
    assert first.monte_carlo_minimum_p == 1 / 10_001
    assert first.extreme_permutations == 0
    assert first.p_value_two_sided == 1 / 10_001


def _accuracy_metric(gold: Sequence[str], pred: Sequence[str]) -> float:
    return sum(g == p for g, p in zip(gold, pred, strict=True)) / len(gold)


def test_accuracy_interval_bootstraps_complete_connected_components() -> None:
    result = MODULE["bootstrap_metrics_by_component"](
        {"a1": "SUPPORTED", "a2": "REFUTED", "b1": "SUPPORTED", "b2": "REFUTED"},
        {"a1": "SUPPORTED", "a2": "REFUTED", "b1": "REFUTED", "b2": "SUPPORTED"},
        {
            "a1": "component:a",
            "a2": "component:a",
            "b1": "component:b",
            "b2": "component:b",
        },
        {"accuracy": _accuracy_metric},
    )

    assert result.ci95 == {"accuracy": (0.0, 1.0)}
    assert result.component_count == 2
    assert result.case_count == 4
    assert result.method == "percentile_component_bootstrap"
    assert result.iterations == 10_000
    assert result.seed == 20261003
    assert result.generator == "RGC-PRNG-1"
    assert result.percentile == "hyndman-fan-type-7"


def test_accuracy_component_bootstrap_rejects_invalid_component_ids() -> None:
    with pytest.raises(ValueError, match="component:"):
        MODULE["bootstrap_metrics_by_component"](
            {"a": "SUPPORTED"},
            {"a": "SUPPORTED"},
            {"a": "component-a"},
            {"accuracy": _accuracy_metric},
        )


def test_component_kappa_bootstrap_excludes_rule_gap_and_is_reproducible() -> None:
    fn = MODULE["bootstrap_cohen_kappa_by_component"]
    annotations_a = {
        "a1": "SUPPORTED",
        "a2": "REFUTED",
        "b1": "UNVERIFIED",
        "b2": "PARTIALLY_SUPPORTED",
        "excluded": "RULE_GAP",
    }
    annotations_b = {
        "a1": "SUPPORTED",
        "a2": "REFUTED",
        "b1": "PARTIALLY_SUPPORTED",
        "b2": "UNVERIFIED",
        "excluded": "SUPPORTED",
    }
    components = {
        "a1": "component:a",
        "a2": "component:a",
        "b1": "component:b",
        "b2": "component:b",
        "excluded": "component:c",
    }

    first = fn(annotations_a, annotations_b, components)
    second = fn(annotations_a, annotations_b, components)

    assert first == second
    assert first.component_count == 2
    assert first.case_count == 4
    assert first.rule_gap_excluded_count == 1
    assert first.rule_gap_excluded_disagreements == 1
    assert first.method == "percentile_component_bootstrap"
    assert first.iterations == 10_000
    assert first.seed == 20261003
    assert first.generator == "RGC-PRNG-1"
    assert first.percentile == "hyndman-fan-type-7"
    assert first.valid_replicates + first.undefined_replicates == 10_000
    assert first.kappa == pytest.approx(1 / 3)
    assert first.ci95 == (-1.0, 1.0)
    assert first.valid_replicates == 10_000
    assert first.undefined_replicates == 0
    assert first.unstable is False


def test_component_kappa_bootstrap_reports_fully_undefined_interval() -> None:
    result = MODULE["bootstrap_cohen_kappa_by_component"](
        {"a": "SUPPORTED", "b": "SUPPORTED"},
        {"a": "SUPPORTED", "b": "SUPPORTED"},
        {"a": "component:a", "b": "component:b"},
    )

    assert result.kappa is None
    assert result.ci95 is None
    assert result.undefined_replicates == 10_000
    assert result.undefined_fraction == 1.0
    assert result.unstable is True


def test_component_kappa_bootstrap_rejects_noncanonical_component_id() -> None:
    with pytest.raises(ValueError, match="component:"):
        MODULE["bootstrap_cohen_kappa_by_component"](
            {"a": "SUPPORTED"},
            {"a": "SUPPORTED"},
            {"a": "component-a"},
        )


def test_component_kappa_bootstrap_rejects_mismatched_case_ids() -> None:
    with pytest.raises(ValueError, match="must match exactly"):
        MODULE["bootstrap_cohen_kappa_by_component"](
            {"a": "SUPPORTED"},
            {"b": "SUPPORTED"},
            {"a": "component:a"},
        )


# --------------------------------------------------------------------------- D4 helpers


def test_component_differences_sum_system_minus_baseline_hits() -> None:
    gold = ["SUPPORTED", "REFUTED", "SUPPORTED", "REFUTED"]
    pred = ["SUPPORTED", "REFUTED", "REFUTED", "REFUTED"]
    base = ["SUPPORTED"] * 4
    units = ["component:syn:a", "component:syn:a", "component:syn:b", "component:syn:b"]
    differences = MODULE["component_differences"](gold, pred, base, units)
    assert differences == {"component:syn:a": 1, "component:syn:b": 0}
    with pytest.raises(ValueError):
        MODULE["component_differences"](gold, pred, base, ["syn:a"] * 4)


def test_obuchowski_reproduces_the_published_clustered_example() -> None:
    # PET/SPECT clustered matched-pair example (21 clusters, 51 units): X^2 about 2.857
    # (2.88 with the proportions rounded to three decimals), p about 0.091.
    n = [3, 3, 3, 1, 3, 4, 3, 2, 2, 1, 3, 2, 3, 2, 2, 3, 3, 3, 2, 1, 2]
    pet = [0, 2, 3, 1, 2, 4, 3, 2, 2, 1, 2, 2, 3, 2, 0, 2, 2, 2, 2, 1, 2]
    spect = [2, 3, 3, 1, 3, 4, 3, 2, 1, 1, 2, 2, 3, 2, 2, 2, 2, 3, 2, 1, 2]
    gold: list[str] = []
    first: list[str] = []
    second: list[str] = []
    units: list[str] = []
    for k, (size, x, y) in enumerate(zip(n, pet, spect, strict=True)):
        for unit in range(size):
            gold.append("SUPPORTED")
            first.append("SUPPORTED" if unit < x else "REFUTED")
            second.append("SUPPORTED" if unit < y else "REFUTED")
            units.append(f"component:syn:k{k:02d}")
    result = MODULE["obuchowski_clustered_test"](gold, first, second, units)
    assert (result.units, result.cases) == (21, 51)
    assert result.variance == pytest.approx(0.00484429, abs=1e-7)
    assert result.chi_square == pytest.approx(2.85714, abs=1e-4)
    assert result.p_value == pytest.approx(0.0909, abs=1e-3)
    assert (0.784 - 0.902) ** 2 / result.variance == pytest.approx(2.88, abs=0.01)


def test_obuchowski_is_undefined_with_one_unit_or_zero_variance() -> None:
    test = MODULE["obuchowski_clustered_test"]
    one = test(["SUPPORTED"], ["SUPPORTED"], ["REFUTED"], ["component:syn:a"])
    assert one.chi_square is None and one.p_value is None and one.variance is None
    tie = test(
        ["SUPPORTED"] * 2,
        ["SUPPORTED"] * 2,
        ["SUPPORTED"] * 2,
        ["component:syn:a", "component:syn:b"],
    )
    assert tie.variance == 0 and tie.chi_square is None


@pytest.mark.parametrize(
    "unit", ["c1", "syn:a", "component:syn:b+syn:a", "component:Syn:A", "", "component:"]
)
def test_obuchowski_rejects_noncanonical_component_ids(unit: str) -> None:
    with pytest.raises(ValueError):
        MODULE["obuchowski_clustered_test"](
            ["SUPPORTED", "SUPPORTED"],
            ["SUPPORTED", "REFUTED"],
            ["REFUTED", "SUPPORTED"],
            ["component:syn:a", unit],
        )


def test_obuchowski_rejects_mismatched_lengths_and_empty_input() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        MODULE["obuchowski_clustered_test"](["SUPPORTED"], [], [], [])
    with pytest.raises(ValueError, match="at least one"):
        MODULE["obuchowski_clustered_test"]([], [], [], [])


def test_component_bootstrap_iterations_are_explicit() -> None:
    result = MODULE["bootstrap_metrics_by_component"](
        {"a": "SUPPORTED"},
        {"a": "SUPPORTED"},
        {"a": "component:syn:a"},
        {"accuracy": lambda g, p: float(g == p)},
        iterations=7,
    )
    assert result.iterations == 7
    with pytest.raises(ValueError, match="iterations"):
        MODULE["bootstrap_metrics_by_component"](
            {"a": "SUPPORTED"},
            {"a": "SUPPORTED"},
            {"a": "component:syn:a"},
            {"accuracy": lambda g, p: float(g == p)},
            iterations=0,
        )
