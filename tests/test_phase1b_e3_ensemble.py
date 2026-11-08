"""E3 fixed-rule ensembles on a synthetic score cache (DEC-024 option B)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmarks.phase1b import e3_ensemble
from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS
from scripts.benchmarks.phase1b.calibration_v2.venn_abers import venn_abers_reference
from scripts.benchmarks.phase1b.e3_ensemble import (
    _tie_break_key,
    combine,
    configuration_cost,
    load_eligibility,
    run_e3,
)
from scripts.benchmarks.phase1b.e3_ivap import ivap, nested_ivap
from scripts.benchmarks.phase1b.score_cache import build_score_cache

PER_COHORT = 60


def _cache(noise: dict[str, float], seed: int = 20261108) -> dict:
    """Three models; independent noise makes averaging informative."""

    rng = np.random.default_rng(seed)
    rows: dict[str, list[dict]] = {model: [] for model in noise}
    for cohort in COHORTS:
        for index in range(PER_COHORT):
            label = index % 2
            record_id = f"{cohort}-{index:03d}"
            for model, sd in noise.items():
                score = float(np.clip(0.5 + (0.12 if label else -0.12) + rng.normal(0, sd), 0, 1))
                rows[model].append(
                    {
                        "record_id": record_id,
                        "cohort": cohort,
                        "gold": "SUPPORTED" if label else "NOT_SUPPORTED",
                        "score": score,
                    }
                )
    return build_score_cache(
        rows,
        protocols={},
        manifest_sha256="m" * 64,
        source_run_id="1",
        calibration_v2=None,
    )


@pytest.fixture(autouse=True)
def _preregistration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prereg = tmp_path / "PREREG-E3-ENSEMBLE-v0.8.md"
    prereg.write_text("**Status:** Aprovado pelo mantenedor em 2026-11-08.\n", encoding="utf-8")
    monkeypatch.setattr(e3_ensemble, "PREREGISTRATION_PATH", prereg)


def test_fixed_rules_have_no_learned_parameters() -> None:
    assert combine([0.2, 0.6], "E3a") == pytest.approx(0.4)
    expected = 1 / (1 + math.exp(-(math.log(0.2 / 0.8) + math.log(0.6 / 0.4)) / 2))
    assert combine([0.2, 0.6], "E3b") == pytest.approx(expected)
    assert combine([0.0, 1.0], "E3b") == pytest.approx(0.5)  # symmetric clipping
    with pytest.raises(ValueError):
        combine([], "E3a")


def test_repository_eligibility_matches_preregistered_list() -> None:
    eligibility = load_eligibility()
    assert eligibility["status"] == "exploratory_pre_ledger"
    assert sorted(eligibility["configurations"]) == ["01", "02", "03", "04", "05"]
    assert eligibility["members"]["factcg"]["blocked_cohorts"] == ["Wice"]
    assert len(eligibility["members"]["hhem"]["blocked_cohorts"]) == len(COHORTS)


def test_e3_reports_configurations_decision_and_bootstrap() -> None:
    cache = _cache({"factcg": 0.10, "minicheck": 0.10, "mdeberta": 0.10})
    report = run_e3(cache)

    assert report["partition"] == "DEV-A cross-fitted"
    assert report["classification"] == "exploratory_pre_ledger"
    configurations = report["configurations"]
    assert configurations["02"]["status"] == "not_evaluable_members_absent_from_cache"
    assert configurations["05"]["status"] == "not_evaluable_members_absent_from_cache"
    for config_id in ("01", "03", "04"):
        entry = configurations[config_id]
        assert entry["status"] == "evaluated"
        assert "Wice" not in entry["common_cohorts"]  # comparator blocked there
        assert len(entry["common_cohorts"]) == len(COHORTS) - 1
        for rule in ("E3a", "E3b"):
            result = entry["rules"][rule]
            assert result["bootstrap"]["k_clusters"] == len(COHORTS) - 1
            assert result["bootstrap"]["replicates"] == 2000
            low, high = result["bootstrap"]["ci95_difference"]
            assert low <= result["gain_vs_comparator"] <= high + 1e-12
    # Averaging three equally informative, independent signals should help.
    assert configurations["04"]["rules"]["E3a"]["gain_vs_comparator"] > 0
    assert report["decision"]["outcome"] in {"ensemble_replaces_factcg", "factcg_remains_baseline"}
    serialized = json.dumps(report)
    assert "record_id" not in serialized
    assert "AggreFact-CNN-000" not in serialized


def test_e3_is_deterministic() -> None:
    cache = _cache({"factcg": 0.10, "minicheck": 0.12, "mdeberta": 0.15})
    assert run_e3(cache)["report_sha256"] == run_e3(cache)["report_sha256"]


def test_e3_refuses_to_run_without_preregistration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(e3_ensemble, "PREREGISTRATION_PATH", Path("/nonexistent/prereg.md"))
    with pytest.raises(RuntimeError, match="preregistration"):
        run_e3(_cache({"factcg": 0.1, "minicheck": 0.1}))


def test_e3_refuses_unapproved_preregistration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text(
        "**Status:** PR Draft; pré-registro documental proposto. Não aprovado para execução.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(e3_ensemble, "PREREGISTRATION_PATH", draft)
    with pytest.raises(RuntimeError, match="not approved"):
        run_e3(_cache({"factcg": 0.1, "minicheck": 0.1}))


def test_repository_preregistration_is_approved() -> None:
    approved_on = e3_ensemble.preregistration_approval(
        e3_ensemble.REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-ENSEMBLE-v0.8.md"
    )
    assert approved_on == "2026-11-08"


def test_e3_rejects_injected_eligibility_with_other_status() -> None:
    eligibility = load_eligibility()
    eligibility["status"] = "confirmatory"
    with pytest.raises(ValueError, match="status"):
        run_e3(_cache({"factcg": 0.1, "minicheck": 0.1}), eligibility=eligibility)


def test_tie_break_prefers_lower_measured_cost_then_fewer_members() -> None:
    cheap = {
        "configuration": "E3a-03",
        "members": 2,
        "cost": configuration_cost(["factcg", "mdeberta"]),
    }
    dear = {
        "configuration": "E3a-01",
        "members": 2,
        "cost": configuration_cost(["factcg", "minicheck"]),
    }
    unmeasured = {
        "configuration": "E3a-02",
        "members": 2,
        "cost": configuration_cost(["factcg", "hhem"]),
    }
    bigger = {"configuration": "E3b-04", "members": 3, "cost": cheap["cost"]}
    assert unmeasured["cost"] is None
    ranked = sorted([unmeasured, bigger, dear, cheap], key=_tie_break_key)
    assert [c["configuration"] for c in ranked] == ["E3a-03", "E3b-04", "E3a-01", "E3a-02"]


@pytest.mark.parametrize("seed", range(6))
def test_fast_ivap_matches_reference(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = int(rng.integers(5, 80))
    scores = rng.integers(0, 9, n) / 8.0 if seed % 2 else rng.random(n)
    labels = rng.integers(0, 2, n)
    queries = np.concatenate([rng.random(20), scores[:5], [0.0, 1.0]])
    fast = ivap(scores, labels, queries)
    reference = venn_abers_reference(scores, labels, queries)
    for key in ("p0", "p1", "p"):
        np.testing.assert_allclose(fast[key], reference[key], rtol=0, atol=1e-12)


def test_nested_ivap_inner_never_sees_outer_fold() -> None:
    rng = np.random.default_rng(7)
    scores = rng.random(150)
    labels = rng.integers(0, 2, 150)
    folds = np.arange(150) % 5
    inner, outer = nested_ivap(scores, labels, folds)

    flipped = labels.copy()
    flipped[folds == 2] = 1 - flipped[folds == 2]
    inner_flipped, outer_flipped = nested_ivap(scores, flipped, folds)
    # Thresholds for outer fold 2 come only from inner[2]; its labels must not matter there.
    np.testing.assert_array_equal(inner[2], inner_flipped[2])
    assert np.isnan(inner[2][folds == 2]).all()
    # Outer predictions of fold 2 come from calibrators that never saw fold 2 either.
    np.testing.assert_array_equal(outer[folds == 2], outer_flipped[folds == 2])
    assert not np.isnan(outer).any()
