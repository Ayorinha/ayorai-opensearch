"""P4-01: the inference score-equivalence harness merges and compares fail-closed.

Scoring itself needs torch and the pinned models and runs in the
phase1b-inference-equivalence workflow; these tests cover the record set and the
comparison rules without them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.benchmarks.phase1b import inference_equivalence as ie

ROOT = Path(__file__).resolve().parents[1]


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


def test_the_shard_loads_the_pinned_tokenizer_json_not_auto_tokenizer() -> None:
    # transformers 5.x AutoTokenizer rebuilds DeBERTa-v2 from spm.model and changes the
    # encodings; the shard must read the revision's tokenizer.json (P4-01).
    source = (ROOT / "scripts/benchmarks/phase1b/run_shard.py").read_text(encoding="utf-8")
    assert "AutoTokenizer.from_pretrained" not in source
    assert "import AutoTokenizer" not in source
    assert ", AutoTokenizer" not in source
    assert "tokenizer = load_pinned_tokenizer(model_dir)" in source
    assert source.count("return_token_type_ids=True") == 2


def test_a_revision_without_tokenizer_json_is_refused(tmp_path: Path) -> None:
    from scripts.benchmarks.phase1b.run_shard import load_pinned_tokenizer

    with pytest.raises(RuntimeError, match="tokenizer.json"):
        load_pinned_tokenizer(tmp_path)


def test_the_equivalence_gate_also_runs_one_package_at_a_time() -> None:
    workflow = (ROOT / ".github/workflows/phase1b-inference-equivalence.yml").read_text(
        encoding="utf-8"
    )
    assert "environment: [historical, current, torch-only, transformers-only]" in workflow
    assert "--compare /tmp/scores-historical.json /tmp/scores-current.json" in workflow
