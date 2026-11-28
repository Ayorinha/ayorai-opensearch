"""P4-01: the inference score-equivalence harness merges and compares fail-closed.

Scoring itself needs torch and the pinned models and runs in the
phase1b-inference-equivalence workflow; these tests cover the record set and the
comparison rules without them.
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.benchmarks.phase1b import inference_equivalence as ie


def _report(model: str, scores: dict[str, float], blocks: int = 3) -> dict[str, Any]:
    return {
        "versions": {"torch": "t", "transformers": "x"},
        "records": len(scores),
        "records_sha256": "same",
        "models": {
            model: {
                "scores": scores,
                "block_count": blocks,
                "token_count_by_unit": {"tokens": 10},
                "truncation_count": 0,
            }
        },
    }


def _env(scores: dict[str, float], blocks: int = 3) -> dict[str, Any]:
    return ie.merge([_report(m, scores, blocks) for m in ie.MODELS])


def test_records_are_deterministic_synthetic_and_cover_three_lengths() -> None:
    first, second = ie.records(), ie.records()
    assert first == second
    assert len(first) == ie.DOCUMENTS * 3
    assert {row["dataset"] for _, row in first} == {
        "synthetic-in-doc",
        "synthetic-perturbed",
        "synthetic-unrelated",
    }
    lengths = sorted({len(row["doc"].split()) for _, row in first})
    assert lengths[0] < 60 < lengths[-1]


def test_identical_scores_are_equivalent() -> None:
    result = ie.compare(_env({"a": 0.2, "b": 0.9}), _env({"a": 0.2, "b": 0.9}))
    assert result["equivalent"] is True


def test_float_noise_below_the_bound_is_equivalent() -> None:
    result = ie.compare(_env({"a": 0.2}), _env({"a": 0.2 + ie.MAX_ABS_DIFF / 2}))
    assert result["equivalent"] is True


@pytest.mark.parametrize(
    ("candidate", "blocks"),
    [({"a": 0.2 + 1e-3}, 3), ({"a": 0.2}, 4)],
)
def test_score_drift_or_different_chunking_is_not_equivalent(
    candidate: dict[str, float], blocks: int
) -> None:
    result = ie.compare(_env({"a": 0.2}), _env(candidate, blocks))
    assert result["equivalent"] is False


def test_a_decision_flip_is_reported() -> None:
    result = ie.compare(_env({"a": 0.4999995}), _env({"a": 0.5000001}))
    assert result["models"]["factcg"]["decision_flips_at_0_5"] == 1
    assert result["equivalent"] is False


def test_merge_refuses_reports_from_different_environments_or_records() -> None:
    other = _report("factcg", {"a": 0.1})
    other["versions"] = {"torch": "other", "transformers": "x"}
    with pytest.raises(SystemExit):
        ie.merge([_report("mdeberta", {"a": 0.1}), other])
    other = _report("factcg", {"a": 0.1})
    other["records_sha256"] = "different"
    with pytest.raises(SystemExit):
        ie.merge([_report("mdeberta", {"a": 0.1}), other])
