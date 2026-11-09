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

_ORIGINAL_LOAD_ELIGIBILITY = e3_confirm.load_eligibility
_ORIGINAL_NON_ESTIMABLE_GATE = e3_confirm._require_non_estimable_rule
_ORIGINAL_ATOMIC_LOCK_GATE = e3_confirm._require_persistent_atomic_lock
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


CLAIMS_PER_DOC = 4


def _doc_id(record_id: str) -> str:
    import hashlib

    cohort, index = record_id.rsplit("-", 1)
    return hashlib.sha256(f"{cohort}|{int(index) // CLAIMS_PER_DOC}".encode()).hexdigest()


def _cache(rows: dict[str, list[dict]], *, v2: bool = True) -> dict:
    cache = build_score_cache(
        rows, protocols={}, manifest_sha256="m" * 64, source_run_id="1", calibration_v2=None
    )
    if v2:
        cache["schema_version"] = "phase1b-dev-score-cache-v2"
        for entry in cache["models"].values():
            for record in entry["records"]:
                record["doc_id"] = _doc_id(record["record_id"])
    return cache


NOISE = {"factcg": 0.12, "minicheck": 0.12, "mdeberta": 0.2}


@pytest.fixture(autouse=True)
def _approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prereg = tmp_path / "PREREG-E3-CONFIRM-DEV-B-v0.8.md"
    prereg.write_text("**Status:** Aprovado pelo mantenedor em 2026-11-08.\n", encoding="utf-8")
    monkeypatch.setattr(e3_confirm, "PREREGISTRATION_PATH", prereg)
    eligibility = _ORIGINAL_LOAD_ELIGIBILITY()
    eligibility["confirmatory_authorization"] = {
        "decision": "DEC-026",
        "status": "approved",
        "scope": "p1-dev-b-confirmatory",
        "approved_on": "2026-11-09",
        "eligibility_sha256": e3_confirm.ELIGIBILITY_SHA256,
        "selection_exposure": {
            "status": "resolved",
            "decision_ref": "TEST-ONLY-SYNTHETIC-DECISION",
        },
    }
    monkeypatch.setattr(e3_confirm, "load_eligibility", lambda: eligibility)
    # Algorithm tests bypass policy gates only to exercise synthetic data paths.
    # Separate tests assert that production gates fail closed.
    monkeypatch.setattr(e3_confirm, "_require_non_estimable_rule", lambda: None)
    monkeypatch.setattr(e3_confirm, "_require_persistent_atomic_lock", lambda: None)


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


def test_estimand_statement_and_loco_are_descriptive() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    assert "No superiority claim is made for any individual cohort" in report["estimand_statement"]
    loco = report["leave_one_cohort_out_delta"]
    assert set(loco) == set(report["common_cohorts"])
    assert report["leave_one_cohort_out_role"].startswith("descriptive")


@pytest.mark.parametrize("defect", ["gold", "cohort", "duplicate", "nan", "range"])
def test_strict_member_validation(defect: str) -> None:
    rows = _rows(NOISE)
    cache = _cache(rows)
    target = cache["models"]["minicheck"]["records"]
    if defect == "gold":
        target[0]["gold"] = "SUPPORTED" if target[0]["gold"] == "NOT_SUPPORTED" else "NOT_SUPPORTED"
        message = "disagrees"
    elif defect == "cohort":
        target[0]["cohort"] = "another-cohort"
        message = "disagrees"
    elif defect == "duplicate":
        target.append(dict(target[0]))
        message = "duplicate"
    elif defect == "nan":
        target[0]["score"] = float("nan")
        message = "outside"
    else:
        target[0]["score"] = 1.5
        message = "outside"
    with pytest.raises(ValueError, match=message):
        run_confirm(cache)


def test_refuses_when_a_confirmation_report_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published = tmp_path / "reports" / "benchmarks" / "2026-12-01-p1-dev-b-confirmation"
    published.mkdir(parents=True)
    monkeypatch.setattr(e3_confirm, "REPOSITORY_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="single-use"):
        run_confirm(_cache(_rows(NOISE)))


def test_eligibility_cannot_be_injected() -> None:
    import inspect

    assert list(inspect.signature(run_confirm).parameters) == ["cache"]


def test_primary_interval_resamples_documents() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    primary = report["primary_interval"]
    assert primary["unit"].startswith("document")
    assert "document clusters" in primary["method"]
    assert set(report["dev_b_documents_by_cohort"]) == set(report["common_cohorts"])
    diagnostics = report["diagnostics"]
    assert diagnostics["role"].startswith("exploratory; not inferential")
    assert diagnostics["document_influence"]["documents_used"] > 0
    assert "bca_interval_95" not in diagnostics
    assert "record" in diagnostics["record_level_bootstrap"]["method"]


def test_document_bootstrap_widens_interval_under_within_document_correlation() -> None:
    """When claims of a document share the same outcome, case resampling is too narrow."""

    from scripts.benchmarks.phase1b.e3_confirm import _document_bootstrap, _document_stats

    rng = np.random.default_rng(11)
    stats = {}
    groups = {}
    for cohort in ("a", "b"):
        y, e, f, docs = [], [], [], []
        for doc in range(30):
            ens_right = rng.random() < 0.8
            cmp_right = rng.random() < 0.7
            for claim in range(8):
                label = claim % 2
                y.append(label)
                e.append(label if ens_right else 1 - label)
                f.append(label if cmp_right else 1 - label)
                docs.append(f"{cohort}-{doc}")
        _, stats[cohort] = _document_stats({"y": y, "e": e, "f": f, "docs": docs})
        groups[cohort] = (y, e, f)
    doc_ci = _document_bootstrap(stats)[0]["ci95_difference"]
    case_ci = e3_confirm._stratified_bootstrap(groups)["ci95_difference"]
    assert (doc_ci[1] - doc_ci[0]) > 1.5 * (case_ci[1] - case_ci[0])


def test_document_stats_match_balanced_accuracy() -> None:
    from scripts.benchmarks.phase1b.calibration import balanced_accuracy
    from scripts.benchmarks.phase1b.e3_confirm import _document_stats, _paired_ba_delta

    rng = np.random.default_rng(5)
    y = rng.integers(0, 2, 60).tolist()
    e = rng.integers(0, 2, 60).tolist()
    f = rng.integers(0, 2, 60).tolist()
    docs = [f"d{i // 3}" for i in range(60)]
    _, stats = _document_stats({"y": y, "e": e, "f": f, "docs": docs})
    delta, invalid = _paired_ba_delta(stats.sum(axis=0))
    assert not invalid
    assert abs(float(delta) - (balanced_accuracy(y, e) - balanced_accuracy(y, f))) < 1e-12


def test_v1_cache_is_refused() -> None:
    with pytest.raises(ValueError, match="v2 score cache"):
        run_confirm(_cache(_rows(NOISE), v2=False))


def test_members_must_agree_on_documents() -> None:
    cache = _cache(_rows(NOISE))
    cache["models"]["minicheck"]["records"][0]["doc_id"] = "0" * 64
    with pytest.raises(ValueError, match="documents"):
        run_confirm(cache)


@pytest.mark.parametrize("defect", ["empty", "single_class"])
def test_dev_b_cohort_must_be_estimable(defect: str, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = _cache(_rows(NOISE))
    target = "ClaimVerify"
    original = e3_confirm.split_dev_a_b

    def patched(ids, cohorts):
        assignments, info = original(ids, cohorts)
        for record_id, cohort in zip(ids, cohorts, strict=True):
            if cohort != target or assignments[record_id] != "DEV-B":
                continue
            if defect == "empty":
                assignments[record_id] = "DEV-A"
            elif int(record_id.rsplit("-", 1)[1]) % 2 == 0:
                assignments[record_id] = "DEV-A"
        return assignments, info

    monkeypatch.setattr(e3_confirm, "split_dev_a_b", patched)
    with pytest.raises(ValueError, match="no DEV-B records|lacks a class"):
        run_confirm(cache)


def test_refuses_until_non_estimable_rule_is_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e3_confirm, "NON_ESTIMABLE_RULE", {"synthetic": True})
    with pytest.raises(RuntimeError, match="non-null rule object is insufficient"):
        _ORIGINAL_NON_ESTIMABLE_GATE()


def test_refuses_without_persistent_atomic_execution_lock() -> None:
    with pytest.raises(RuntimeError, match="persistent single-use Git ref"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


def test_refuses_when_dec026_has_no_confirmatory_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e3_confirm, "load_eligibility", _ORIGINAL_LOAD_ELIGIBILITY)
    with pytest.raises(RuntimeError, match="DEC-026"):
        run_confirm(_cache(_rows(NOISE)))


def test_confirmatory_eligibility_is_bound_to_matrix_and_selection_decision() -> None:
    eligibility = _ORIGINAL_LOAD_ELIGIBILITY()
    with pytest.raises(RuntimeError, match="DEC-026"):
        e3_confirm._validate_confirmatory_eligibility(
            eligibility, eligibility_sha256=e3_confirm.ELIGIBILITY_SHA256
        )
