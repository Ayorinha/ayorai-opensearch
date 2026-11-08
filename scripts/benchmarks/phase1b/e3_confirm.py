"""P1 — single confirmation of E3b-01 against FactCG on DEV-B (roadmap v0.8).

Implements docs/benchmarks/PREREG-E3-CONFIRM-DEV-B-v0.8.md under DEC-024 option B and
DEC-025:
- one hypothesis: E3b-01 (factcg + minicheck, mean of clipped logits) vs FactCG;
- IVAP calibrators fitted on all of DEV-A produce the DEV-B probabilities;
- per-cohort thresholds are chosen on DEV-A out-of-fold probabilities (Calibration V2
  folds) and applied once to DEV-B; no DEV-B label enters any fitted quantity;
- primary interval: paired bootstrap stratified by cohort (records resampled within each
  cohort), 2,000 replicates, PCG64(20261109); secondary: cohort-cluster bootstrap;
- CONFIRMED only if delta >= 0.005 and the primary 95% lower bound > 0.

Output is aggregate-only. TEST is never used.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.benchmarks.phase1b.calibration import balanced_accuracy, calibrate_by_cohort
from scripts.benchmarks.phase1b.calibration_v2.splits import crossfit_folds, split_dev_a_b
from scripts.benchmarks.phase1b.common import canonical_json, sha256_bytes
from scripts.benchmarks.phase1b.e3_ensemble import (
    ELIGIBILITY_PATH,
    REPLACEMENT_MARGIN,
    REPOSITORY_ROOT,
    _eligible,
    _paired_bootstrap,
    _validate_eligibility,
    combine,
    load_eligibility,
    preregistration_approval,
)
from scripts.benchmarks.phase1b.e3_ivap import ivap

PREREGISTRATION_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-CONFIRM-DEV-B-v0.8.md"
ELIGIBILITY_SHA256 = "8b7becf74727a1ad1d52706760c9682b04bd1805476bf3c0c0adddefa1f569f4"
COMPARATOR = "factcg"
MEMBERS = ("factcg", "minicheck")
RULE = "E3b"
CONFIGURATION = "E3b-01"
STRATIFIED_REPLICATES = 2000
STRATIFIED_SEED = 20261109
MAX_INVALID_FRACTION = 0.05
# Single-execution lock (persistent part): a published P1 report in the repository.
REPORT_LOCK_GLOB = "reports/benchmarks/*p1-dev-b-confirmation*"
ESTIMAND_STATEMENT = (
    "The estimand is the macro balanced accuracy over the common cohorts. No superiority "
    "claim is made for any individual cohort; per-cohort values are descriptive."
)


def published_confirmation_exists(root: Path | None = None) -> bool:
    """True when a P1 confirmation report is already published (execution is single-use)."""

    root = root if root is not None else REPOSITORY_ROOT
    return any(root.glob(REPORT_LOCK_GLOB))


def validate_members(models: Mapping[str, Any]) -> list[str]:
    """Strict cross-member checks; returns the sorted record ids."""

    missing = [member for member in MEMBERS if member not in models]
    if missing:
        raise ValueError(f"the score cache lacks members: {missing}")
    reference: dict[str, tuple[str, str]] | None = None
    for member in MEMBERS:
        seen: dict[str, tuple[str, str]] = {}
        for record in models[member]["records"]:
            record_id = record["record_id"]
            if record_id in seen:
                raise ValueError(f"{member} has a duplicate record_id")
            if record["gold"] not in {"SUPPORTED", "NOT_SUPPORTED"}:
                raise ValueError(f"{member} has an invalid gold label")
            score = record["score"]
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError(f"{member} has a non-numeric score")
            if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
                raise ValueError(f"{member} has a score outside [0, 1]")
            seen[record_id] = (record["cohort"], record["gold"])
        if reference is None:
            reference = seen
        elif seen != reference:
            raise ValueError(f"{member} disagrees with {MEMBERS[0]} on records, cohorts or labels")
    return sorted(reference or {})


def leave_one_cohort_out(
    ba_by_arm: Mapping[str, Mapping[str, float]], common: Sequence[str]
) -> dict[str, float]:
    """Descriptive only: macro delta recomputed without each cohort in turn."""

    result: dict[str, float] = {}
    for left_out in common:
        kept = [cohort for cohort in common if cohort != left_out]
        result[left_out] = sum(
            ba_by_arm["ensemble"][c] - ba_by_arm["comparator"][c] for c in kept
        ) / len(kept)
    return result


def _out_of_fold(scores: Sequence[float], labels: Sequence[int], folds: Sequence[int]) -> list:
    import numpy as np

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.int64)
    fold_array = np.asarray(folds, dtype=np.int64)
    values = np.full(score_array.size, np.nan, dtype=np.float64)
    for fold in np.unique(fold_array):
        held = fold_array == fold
        values[held] = ivap(score_array[~held], label_array[~held], score_array[held])["p"]
    if np.isnan(values).any():
        raise ArithmeticError("out-of-fold IVAP did not cover every DEV-A record")
    return values.tolist()


def _replicate_ba(predictions: Any, labels: Any, positives: Any, negatives: Any) -> Any:
    tpr = (predictions * labels).sum(axis=1) / positives
    tnr = ((1 - predictions) * (1 - labels)).sum(axis=1) / negatives
    return (tpr + tnr) / 2.0


def _stratified_bootstrap(
    groups: Mapping[str, tuple[Sequence[int], Sequence[int], Sequence[int]]],
) -> dict[str, Any]:
    """Paired bootstrap; records resampled within each cohort; cohorts are fixed."""

    import numpy as np

    rng = np.random.Generator(np.random.PCG64(STRATIFIED_SEED))
    differences = np.zeros(STRATIFIED_REPLICATES, dtype=np.float64)
    invalid = np.zeros(STRATIFIED_REPLICATES, dtype=bool)
    for cohort in sorted(groups):
        labels, ensemble, comparator = (np.asarray(v, dtype=np.int64) for v in groups[cohort])
        draws = rng.integers(0, labels.size, size=(STRATIFIED_REPLICATES, labels.size))
        y = labels[draws]
        positives = y.sum(axis=1)
        negatives = labels.size - positives
        bad = (positives == 0) | (negatives == 0)
        invalid |= bad
        safe_pos = np.where(bad, 1, positives)
        safe_neg = np.where(bad, 1, negatives)

        differences += _replicate_ba(ensemble[draws], y, safe_pos, safe_neg) - _replicate_ba(
            comparator[draws], y, safe_pos, safe_neg
        )
    differences /= len(groups)
    valid = differences[~invalid]
    invalid_count = int(invalid.sum())
    estimable = invalid_count <= MAX_INVALID_FRACTION * STRATIFIED_REPLICATES and valid.size > 1
    low, high = (
        (float(v) for v in np.quantile(valid, [0.025, 0.975], method="linear"))
        if estimable
        else (None, None)
    )
    return {
        "method": "paired bootstrap stratified by cohort (records resampled within cohort)",
        "replicates": STRATIFIED_REPLICATES,
        "invalid_replicates": invalid_count,
        "estimable": bool(estimable),
        "generator": f"numpy.random.Generator(PCG64({STRATIFIED_SEED}))",
        "numpy_version": np.__version__,
        "quantile_method": "linear",
        "ci95_difference": [low, high],
    }


def run_confirm(cache: Mapping[str, Any]) -> dict:
    """Single execution of P1; the only eligibility accepted is the preregistered file."""

    approved_on = preregistration_approval(PREREGISTRATION_PATH)
    if published_confirmation_exists():
        raise RuntimeError("a P1 confirmation report is already published; P1 is single-use")
    file_sha256 = sha256_bytes(Path(ELIGIBILITY_PATH).read_bytes())
    if file_sha256 != ELIGIBILITY_SHA256:
        raise RuntimeError("eligibility file differs from the preregistered version")
    eligibility = load_eligibility()
    _validate_eligibility(eligibility)
    models = cache["models"]
    record_ids = validate_members(models)
    reference = {r["record_id"]: r for r in models[COMPARATOR]["records"]}
    cohorts = [reference[r]["cohort"] for r in record_ids]
    labels = [1 if reference[r]["gold"] == "SUPPORTED" else 0 for r in record_ids]

    common = [c for c in eligibility["cohorts"] if _eligible(eligibility, COMPARATOR, c)]
    for cohort in common:
        if not all(_eligible(eligibility, member, cohort) for member in MEMBERS):
            raise ValueError(f"a member is blocked in common cohort {cohort}")
    common_set = set(common)

    assignments, _ = split_dev_a_b(record_ids, cohorts)
    index_a = [i for i, r in enumerate(record_ids) if assignments[r] == "DEV-A"]
    index_b = [i for i, r in enumerate(record_ids) if assignments[r] == "DEV-B"]
    ids_a = [record_ids[i] for i in index_a]
    cohorts_a = [cohorts[i] for i in index_a]
    labels_a = [labels[i] for i in index_a]
    folds, limitations = crossfit_folds(ids_a, cohorts_a, labels_a)
    if limitations:
        raise ValueError("DEV-A has cross-fitting strata below five")
    fold_list = [folds[r] for r in ids_a]

    oof_a: dict[str, list[float]] = {}
    prob_b: dict[str, list[float]] = {}
    for member in MEMBERS:
        scores = {r["record_id"]: r["score"] for r in models[member]["records"]}
        scores_a = [scores[r] for r in ids_a]
        scores_b = [scores[record_ids[i]] for i in index_b]
        oof_a[member] = _out_of_fold(scores_a, labels_a, fold_list)
        prob_b[member] = [float(v) for v in ivap(scores_a, labels_a, scores_b)["p"]]

    keep_a = [k for k, cohort in enumerate(cohorts_a) if cohort in common_set]
    keep_b = [k for k, i in enumerate(index_b) if cohorts[i] in common_set]
    arms = {"ensemble": list(MEMBERS), "comparator": [COMPARATOR]}
    predictions: dict[str, list[int]] = {}
    thresholds: dict[str, dict[str, float]] = {}
    for arm, members in arms.items():
        combined_a = [combine([oof_a[m][k] for m in members], RULE) for k in keep_a]
        thresholds[arm] = calibrate_by_cohort(
            combined_a, [labels_a[k] for k in keep_a], [cohorts_a[k] for k in keep_a]
        )
        predictions[arm] = [
            int(
                combine([prob_b[m][k] for m in members], RULE)
                > thresholds[arm][cohorts[index_b[k]]]
            )
            for k in keep_b
        ]

    labels_b = [labels[index_b[k]] for k in keep_b]
    cohorts_b = [cohorts[index_b[k]] for k in keep_b]
    groups: dict[str, tuple[list[int], list[int], list[int]]] = {}
    ba_by_arm: dict[str, dict[str, float]] = {"ensemble": {}, "comparator": {}}
    counts: dict[str, int] = {}
    for cohort in common:
        members_idx = [j for j, c in enumerate(cohorts_b) if c == cohort]
        y = [labels_b[j] for j in members_idx]
        e = [predictions["ensemble"][j] for j in members_idx]
        f = [predictions["comparator"][j] for j in members_idx]
        groups[cohort] = (y, e, f)
        counts[cohort] = len(members_idx)
        ba_by_arm["ensemble"][cohort] = balanced_accuracy(y, e)
        ba_by_arm["comparator"][cohort] = balanced_accuracy(y, f)

    macro_e = sum(ba_by_arm["ensemble"].values()) / len(common)
    macro_c = sum(ba_by_arm["comparator"].values()) / len(common)
    delta = macro_e - macro_c
    primary = _stratified_bootstrap(groups)
    secondary = _paired_bootstrap(
        [ba_by_arm["ensemble"][c] - ba_by_arm["comparator"][c] for c in common]
    )
    low, high = primary["ci95_difference"]
    confirmed = primary["estimable"] and delta >= REPLACEMENT_MARGIN and low > 0
    outcome = "CONFIRMED" if confirmed else "NOT_CONFIRMED"
    contrary = bool(primary["estimable"] and high is not None and high < 0)

    report: dict[str, Any] = {
        "schema_version": "phase1b-dev-e3-confirm-v1",
        "split": "dev",
        "partition": "DEV-B confirmation (calibrated on DEV-A)",
        "experiment": "e3-confirm-dev-b",
        "decision_record": "DEC-024 option B; DEC-025",
        "preregistration": "docs/benchmarks/PREREG-E3-CONFIRM-DEV-B-v0.8.md",
        "preregistration_approved_on": approved_on,
        "hypothesis": f"{CONFIGURATION} macro BA > {COMPARATOR} macro BA on DEV-B",
        "configuration": CONFIGURATION,
        "members": list(MEMBERS),
        "rule": RULE,
        "eligibility_classification": eligibility["status"],
        "eligibility_sha256": sha256_bytes(canonical_json(dict(eligibility))),
        "source_run_id": cache["source_run_id"],
        "manifest_sha256": cache["manifest_sha256"],
        "record_count": cache["record_count"],
        "dev_a_count": len(index_a),
        "dev_b_count": len(index_b),
        "dev_b_evaluated_count": len(keep_b),
        "common_cohorts": common,
        "dev_b_count_by_cohort": counts,
        "thresholds_by_cohort": thresholds,
        "ba_by_cohort": ba_by_arm,
        "macro_ba": {"ensemble": macro_e, "comparator": macro_c},
        "delta": delta,
        "replacement_margin": REPLACEMENT_MARGIN,
        "primary_interval": primary,
        "secondary_cluster_bootstrap": secondary,
        "leave_one_cohort_out_delta": leave_one_cohort_out(ba_by_arm, common),
        "leave_one_cohort_out_role": "descriptive diagnostic; no effect on the decision",
        "estimand_statement": ESTIMAND_STATEMENT,
        "outcome": outcome,
        "contrary_evidence": contrary,
        "instance_level_output_published": False,
    }
    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report
