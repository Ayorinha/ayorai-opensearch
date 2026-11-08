"""P1 — DEV-B confirmation of E3b-01 on a synthetic score cache (DEC-024 B, DEC-025)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmarks.phase1b import e3_confirm
from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS
from scripts.benchmarks.phase1b.calibration_v2.splits import split_dev_a_b
from scripts.benchmarks.phase1b.e3_confirm import _stratified_bootstrap, run_confirm
from scripts.benchmarks.phase1b.score_cache import EXPERIMENTS, build_score_cache

PER_COHORT = 80


def _rows(noise: dict[str, float], seed: int = 3) -> dict[str, list[dict]]:
    rng = np.random.default_rng(seed)
    rows: dict[str, list[dict]] = {model: [] for model in noise}
    for cohort in COHORTS:
        for index in range(PER_COHORT):
            label = index % 2
            for model, sd in noise.items():
                score = float(np.clip(0.5 + (0.12 if label else -0.12) + rng.normal(0, sd), 0, 1))
                rows[model].append(
                    {
                        "record_id": f"{cohort}-{index:03d}",
                        "cohort": cohort,
                        "gold": "SUPPORTED" if label else "NOT_SUPPORTED",
                        "score": score,
                    }
                )
    return rows


def _cache(rows: dict[str, list[dict]]) -> dict:
    return build_score_cache(
        rows, protocols={}, manifest_sha256="m" * 64, source_run_id="1", calibration_v2=None
    )


NOISE = {"factcg": 0.12, "minicheck": 0.12, "mdeberta": 0.2}


@pytest.fixture(autouse=True)
def _approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prereg = tmp_path / "PREREG-E3-CONFIRM-DEV-B-v0.8.md"
    prereg.write_text("**Status:** Aprovado pelo mantenedor em 2026-11-08.\n", encoding="utf-8")
    monkeypatch.setattr(e3_confirm, "PREREGISTRATION_PATH", prereg)


def test_confirmation_report_is_aggregate_and_complete() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    assert report["experiment"] == "e3-confirm-dev-b"
    assert report["configuration"] == "E3b-01"
    assert report["outcome"] in {"CONFIRMED", "NOT_CONFIRMED"}
    assert "Wice" not in report["common_cohorts"]
    assert len(report["common_cohorts"]) == len(COHORTS) - 1
    assert report["dev_a_count"] + report["dev_b_count"] == report["record_count"]
    primary = report["primary_interval"]
    assert primary["replicates"] == 2000 and primary["estimable"] is True
    low, high = primary["ci95_difference"]
    assert low <= report["delta"] <= high + 1e-12
    # Two equally informative, independent members: averaging should help.
    assert report["delta"] > 0
    serialized = json.dumps(report)
    assert "record_id" not in serialized
    assert "AggreFact-CNN-000" not in serialized


def test_confirmation_is_deterministic() -> None:
    cache = _cache(_rows(NOISE))
    assert run_confirm(cache)["report_sha256"] == run_confirm(cache)["report_sha256"]


def test_dev_b_labels_never_reach_fitted_quantities() -> None:
    rows = _rows(NOISE)
    ids = sorted({r["record_id"] for r in rows["factcg"]})
    cohorts = {r["record_id"]: r["cohort"] for r in rows["factcg"]}
    assignments, _ = split_dev_a_b(ids, [cohorts[r] for r in ids])
    flipped = {
        model: [
            dict(
                r,
                gold=(
                    ("NOT_SUPPORTED" if r["gold"] == "SUPPORTED" else "SUPPORTED")
                    if assignments[r["record_id"]] == "DEV-B"
                    else r["gold"]
                ),
            )
            for r in records
        ]
        for model, records in rows.items()
    }
    original = run_confirm(_cache(rows))
    altered = run_confirm(_cache(flipped))
    assert original["thresholds_by_cohort"] == altered["thresholds_by_cohort"]
    assert original["ba_by_cohort"] != altered["ba_by_cohort"]


def test_refuses_repository_preregistration_until_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        e3_confirm,
        "PREREGISTRATION_PATH",
        e3_confirm.REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-CONFIRM-DEV-B-v0.8.md",
    )
    with pytest.raises(RuntimeError, match="not approved|not on this revision"):
        run_confirm(_cache(_rows(NOISE)))


def test_refuses_changed_eligibility_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(e3_confirm, "ELIGIBILITY_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="eligibility"):
        run_confirm(_cache(_rows(NOISE)))


def test_refuses_cache_without_members() -> None:
    with pytest.raises(ValueError, match="lacks members"):
        run_confirm(_cache(_rows({"factcg": 0.1, "mdeberta": 0.1})))


def test_identical_arms_give_zero_interval() -> None:
    y = [0, 1] * 30
    p = [0, 1, 1, 0] * 15
    result = _stratified_bootstrap({"a": (y, p, p), "b": (y, p, p)})
    assert result["ci95_difference"] == [0.0, 0.0]
    assert result["invalid_replicates"] == 0


def test_experiment_is_registered() -> None:
    assert "e3-confirm-dev-b" in EXPERIMENTS
