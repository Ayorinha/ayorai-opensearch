"""Synthetic tests for DEC-023 connected article components."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_components.py"))


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
    expected_hash = hashlib.sha256(expected_json.encode("utf-8")).hexdigest()
    assert result.components[0].component_id == f"component:sha256:{expected_hash}"
    assert result.components[0].canonical_article_ids_json == expected_json
    assert result.components[0].case_ids == ("case-a", "case-b", "case-c")
    assert result.components[1].article_ids == ("art-9",)
    assert result.components[1].canonical_article_ids_json == '["art-9"]'


def test_component_output_is_independent_of_input_order() -> None:
    cases = [
        {"case_id": "b", "cited_article_ids": ["z", "x"]},
        {"case_id": "a", "cited_article_ids": ["x"]},
        {"case_id": "c", "cited_article_ids": ["q"]},
    ]

    forward = MODULE["build_article_components"](cases)
    reverse = MODULE["build_article_components"](list(reversed(cases)))

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
        MODULE["build_article_components"](cases)


def test_plus_is_safe_inside_article_ids_under_json_hash_serialization() -> None:
    result = MODULE["build_article_components"](
        [{"case_id": "a", "cited_article_ids": ["x+y"]}]
    )

    assert result.components[0].article_ids == ("x+y",)
    assert result.components[0].canonical_article_ids_json == '["x+y"]'
    assert result.components[0].component_id.startswith("component:sha256:")


def test_non_nfc_article_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="NFC"):
        MODULE["build_article_components"](
            [{"case_id": "a", "cited_article_ids": ["e\u0301"]}]
        )


def test_empty_input_has_a_well_formed_empty_summary() -> None:
    result = MODULE["build_article_components"]([])

    assert result.components == ()
    assert result.component_count == 0
    assert result.case_count == 0
    assert result.largest_component_size == 0
    assert result.component_sizes == ()


def test_exact_sign_flip_enumerates_all_sign_combinations() -> None:
    result = MODULE["exact_sign_flip"]([1, 1])

    assert result.statistic_observed == 2
    assert result.permutations_considered == 4
    assert result.extreme_permutations == 2
    assert result.p_value_two_sided == 0.5
    assert result.minimum_resolution == 0.5
    assert result.significance_below_005_possible is False


def test_exact_sign_flip_keeps_zero_difference_components() -> None:
    result = MODULE["exact_sign_flip"]([1, 0])

    assert result.component_count == 2
    assert result.permutations_considered == 4
    assert result.p_value_two_sided == 1.0


def test_exact_sign_flip_is_symmetric_and_deterministic() -> None:
    fn = MODULE["exact_sign_flip"]
    positive = fn([3, -2, 1])
    negative = fn([-3, 2, -1])

    assert positive.statistic_observed == -negative.statistic_observed
    assert positive.p_value_two_sided == negative.p_value_two_sided
    assert positive.extreme_permutations == negative.extreme_permutations
    assert positive.permutations_considered == negative.permutations_considered


def test_exact_sign_flip_rejects_empty_and_non_integer_inputs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        MODULE["exact_sign_flip"]([])
    with pytest.raises(ValueError, match="integers"):
        MODULE["exact_sign_flip"]([1, True])


def test_exact_sign_flip_refuses_unspecified_monte_carlo_path() -> None:
    with pytest.raises(ValueError, match="PRNG specification"):
        MODULE["exact_sign_flip"]([1] * 21)



def test_monte_carlo_sign_flip_uses_fixed_reproducible_pcg64() -> None:
    fn = MODULE["exact_sign_flip"]
    first = fn([1] * 21)
    second = fn([1] * 21)

    assert first == second
    assert first.method == "monte_carlo"
    assert first.seed == 20261003
    assert first.generator == "numpy.random.Generator(numpy.random.PCG64)"
    assert first.iterations == 10_000
    assert first.permutations_considered == 10_000
    assert first.p_value_two_sided == (1 + first.extreme_permutations) / 10_001
    assert first.minimum_resolution == 2 / (2**21)


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
        "a1": "component-a",
        "a2": "component-a",
        "b1": "component-b",
        "b2": "component-b",
        "excluded": "component-c",
    }

    first = fn(annotations_a, annotations_b, components)
    second = fn(annotations_a, annotations_b, components)

    assert first == second
    assert first.component_count == 2
    assert first.case_count == 4
    assert first.iterations == 10_000
    assert first.seed == 20261003
    assert first.generator == "numpy.random.Generator(numpy.random.PCG64)"
    assert first.valid_replicates + first.undefined_replicates == 10_000
    assert first.ci95 is not None
    assert first.unstable == (first.undefined_fraction > 0.05)


def test_component_kappa_bootstrap_reports_fully_undefined_interval() -> None:
    result = MODULE["bootstrap_cohen_kappa_by_component"](
        {"a": "SUPPORTED", "b": "SUPPORTED"},
        {"a": "SUPPORTED", "b": "SUPPORTED"},
        {"a": "component-a", "b": "component-b"},
    )

    assert result.kappa is None
    assert result.ci95 is None
    assert result.undefined_replicates == 10_000
    assert result.undefined_fraction == 1.0
    assert result.unstable is True


def test_component_kappa_bootstrap_rejects_mismatched_case_ids() -> None:
    with pytest.raises(ValueError, match="must match exactly"):
        MODULE["bootstrap_cohen_kappa_by_component"](
            {"a": "SUPPORTED"},
            {"b": "SUPPORTED"},
            {"a": "component-a"},
        )
