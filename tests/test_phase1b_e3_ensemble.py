"""E3 fixed-rule ensembles on a synthetic score cache (DEC-024 option B)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmarks.phase1b import e3_ensemble
from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS
from scripts.benchmarks.phase1b.e3_ensemble import combine, load_eligibility, run_e3
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
    prereg.write_text("synthetic stand-in\n", encoding="utf-8")
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
