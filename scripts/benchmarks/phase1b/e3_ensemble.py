"""E3 — fixed-rule ensembles on the encrypted DEV score cache (roadmap v0.8).

Implements docs/benchmarks/PREREG-E3-ENSEMBLE-v0.8.md under DEC-024 option B:
- E3a: arithmetic mean of cross-fitted IVAP probabilities of the eligible members;
- E3b: mean of logits of those probabilities, clipped to [1e-6, 1 - 1e-6];
- no learned weights; membership per cohort comes only from the eligibility file;
- primary metric: macro BA over cohorts, cross-fitted in DEV-A with per-cohort
  thresholds (same folds and threshold procedure as Calibration V2 Layer 1);
- decision: an ensemble replaces FactCG only if it gains >= 0.005 macro BA on the
  same cohorts and folds;
- uncertainty: paired cohort-cluster bootstrap, 2,000 replicates, PCG64(20261108),
  linear-interpolated 95% percentile interval.

Comparator choice (documented, fixed before results): the paired comparator is FactCG
passed through the identical pipeline, so the comparison is like-for-like.

Nested cross-fitting (no leakage between steps): for each outer DEV-A fold ``k``, the
per-cohort thresholds are chosen on inner out-of-fold IVAP probabilities of the other
folds, whose calibrators never see fold ``k``; the records of fold ``k`` are then scored by
a calibrator fitted on the other folds only. See ``e3_ivap.nested_ivap``.

Fail-closed: the run refuses unless the preregistration on this revision carries the
maintainer approval status line and the eligibility matrix has an accepted status.

Tie-break (preregistration section 6): among qualifying candidates within 0.005 macro BA
of the best, the lowest measured operational cost wins (sum of the members' measured
costs); a candidate with an unmeasured member ranks after measured ones; remaining ties
go to fewer members.

DEV-B and TEST are never used. Output is aggregate-only.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.benchmarks.phase1b.calibration import balanced_accuracy, calibrate_by_cohort
from scripts.benchmarks.phase1b.calibration_v2.aggregate import MODEL_COST_SECONDS
from scripts.benchmarks.phase1b.calibration_v2.splits import crossfit_folds, split_dev_a_b
from scripts.benchmarks.phase1b.common import canonical_json, sha256_bytes
from scripts.benchmarks.phase1b.e3_ivap import nested_ivap

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ELIGIBILITY_PATH = REPOSITORY_ROOT / "configs" / "benchmarks" / "e3-eligibility-v0.8.json"
PREREGISTRATION_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-ENSEMBLE-v0.8.md"
CLIP = 1e-6
REPLACEMENT_MARGIN = 0.005
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261108
RULES = ("E3a", "E3b")
ACCEPTED_ELIGIBILITY_STATUSES = frozenset({"exploratory_pre_ledger"})
APPROVAL_LINE = re.compile(
    r"^\*\*Status:\*\* Aprovado pelo mantenedor em (\d{4}-\d{2}-\d{2})\b", re.MULTILINE
)


def preregistration_approval(path: Path | None = None) -> str:
    """Return the approval date, or refuse when the preregistration is absent or not approved."""

    path = path if path is not None else PREREGISTRATION_PATH
    if not path.is_file():
        raise RuntimeError("E3 preregistration is not on this revision; refusing to run")
    match = APPROVAL_LINE.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(
            "E3 preregistration is not approved by the maintainer "
            "(expected '**Status:** Aprovado pelo mantenedor em YYYY-MM-DD'); refusing to run"
        )
    return match.group(1)


def _validate_eligibility(eligibility: Mapping[str, Any]) -> None:
    if eligibility.get("schema_version") != "phase1b-e3-eligibility-v1":
        raise ValueError("unsupported E3 eligibility file")
    if eligibility.get("status") not in ACCEPTED_ELIGIBILITY_STATUSES:
        raise ValueError(f"E3 eligibility status is not accepted: {eligibility.get('status')!r}")
    cohorts = set(eligibility["cohorts"])
    for member, entry in eligibility["members"].items():
        unknown = set(entry["blocked_cohorts"]) - cohorts
        if unknown:
            raise ValueError(f"{member} blocks unknown cohorts: {sorted(unknown)}")
    if eligibility["comparator"] not in eligibility["members"]:
        raise ValueError("the comparator must be a listed member")
    for config_id, members in eligibility["configurations"].items():
        if eligibility["comparator"] not in members:
            raise ValueError(f"configuration {config_id} must contain the comparator")
        missing = set(members) - set(eligibility["members"])
        if missing:
            raise ValueError(f"configuration {config_id} has unknown members: {sorted(missing)}")


def configuration_cost(members: Sequence[str]) -> float | None:
    """Sum of measured member costs; ``None`` when any member has no measured cost."""

    if any(member not in MODEL_COST_SECONDS for member in members):
        return None
    return round(sum(MODEL_COST_SECONDS[member] for member in members), 6)


def _tie_break_key(candidate: Mapping[str, Any]) -> tuple:
    cost = candidate["cost"]
    return (
        cost is None,
        cost if cost is not None else 0.0,
        candidate["members"],
        candidate["configuration"],
    )


def _logit(probability: float) -> float:
    value = min(1.0 - CLIP, max(CLIP, probability))
    return math.log(value / (1.0 - value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def combine(probabilities: Sequence[float], rule: str) -> float:
    """Apply a fixed E3 rule to the probabilities of the eligible members."""

    if not probabilities:
        raise ValueError("an ensemble needs at least one eligible member")
    if rule == "E3a":
        return sum(probabilities) / len(probabilities)
    if rule == "E3b":
        return _sigmoid(sum(_logit(p) for p in probabilities) / len(probabilities))
    raise ValueError(f"unknown E3 rule: {rule}")


def load_eligibility(path: Path = ELIGIBILITY_PATH) -> dict[str, Any]:
    eligibility = json.loads(path.read_text(encoding="utf-8"))
    _validate_eligibility(eligibility)
    return eligibility


def _eligible(eligibility: Mapping[str, Any], member: str, cohort: str) -> bool:
    return cohort not in eligibility["members"][member]["blocked_cohorts"]


def _paired_bootstrap(differences: Sequence[float]) -> dict[str, Any]:
    import numpy as np

    values = np.asarray(differences, dtype=np.float64)
    k = values.size
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    draws = rng.integers(0, k, size=(BOOTSTRAP_REPLICATES, k))
    replicates = values[draws].mean(axis=1)
    low, high = np.quantile(replicates, [0.025, 0.975], method="linear")
    return {
        "cluster_unit": "cohort",
        "k_clusters": int(k),
        "replicates": BOOTSTRAP_REPLICATES,
        "invalid_replicates": 0,
        "generator": f"numpy.random.Generator(PCG64({BOOTSTRAP_SEED}))",
        "numpy_version": np.__version__,
        "quantile_method": "linear",
        "ci95_difference": [float(low), float(high)],
        "replicate_mean": float(replicates.mean()),
        "replicate_sd": float(replicates.std(ddof=1)) if k > 1 else 0.0,
        "limitation": "few cohort clusters; interval is approximate and potentially unstable",
    }


def _nested_threshold_ba(
    cohorts: Sequence[str],
    labels: Sequence[int],
    folds: Sequence[int],
    inner: Mapping[int, Sequence[float]],
    outer: Sequence[float],
) -> dict[str, float]:
    """Per-cohort BA with thresholds chosen only on inner probabilities of the training folds."""

    predictions: list[int | None] = [None] * len(labels)
    for outer_fold, inner_values in sorted(inner.items()):
        train = [i for i, fold in enumerate(folds) if fold != outer_fold]
        thresholds = calibrate_by_cohort(
            [float(inner_values[i]) for i in train],
            [labels[i] for i in train],
            [cohorts[i] for i in train],
        )
        for index, fold in enumerate(folds):
            if fold != outer_fold:
                continue
            threshold = thresholds.get(cohorts[index])
            if threshold is None:
                raise ValueError("held-out cohort has no eligible training threshold")
            predictions[index] = int(outer[index] > threshold)
    if any(prediction is None for prediction in predictions):
        raise ArithmeticError("nested evaluation did not cover every DEV-A record")
    result: dict[str, float] = {}
    for cohort in sorted(set(cohorts)):
        members = [i for i, value in enumerate(cohorts) if value == cohort]
        result[cohort] = balanced_accuracy(
            [labels[i] for i in members], [int(predictions[i]) for i in members]
        )
    return result


def run_e3(cache: Mapping[str, Any], eligibility: Mapping[str, Any] | None = None) -> dict:
    """Evaluate every preregistered configuration and rule that the cache supports."""

    approved_on = preregistration_approval()
    eligibility = eligibility if eligibility is not None else load_eligibility()
    _validate_eligibility(eligibility)
    comparator = eligibility["comparator"]
    models = cache["models"]
    if comparator not in models:
        raise ValueError("the score cache does not contain the comparator model")

    reference = {r["record_id"]: r for r in models[comparator]["records"]}
    record_ids = sorted(reference)
    cohorts = [reference[record_id]["cohort"] for record_id in record_ids]
    labels = [1 if reference[record_id]["gold"] == "SUPPORTED" else 0 for record_id in record_ids]
    for model, entry in models.items():
        if {r["record_id"] for r in entry["records"]} != set(record_ids):
            raise ValueError(f"{model} does not cover the same DEV records")

    assignments, _ = split_dev_a_b(record_ids, cohorts)
    dev_a = [i for i, record_id in enumerate(record_ids) if assignments[record_id] == "DEV-A"]
    ids_a = [record_ids[i] for i in dev_a]
    cohorts_a = [cohorts[i] for i in dev_a]
    labels_a = [labels[i] for i in dev_a]
    folds_a, limitations = crossfit_folds(ids_a, cohorts_a, labels_a)
    if limitations:
        raise ValueError("DEV-A has cross-fitting strata below five")
    fold_list = [folds_a[record_id] for record_id in ids_a]

    inner_by_model: dict[str, dict[int, Any]] = {}
    outer_by_model: dict[str, Any] = {}
    for model, entry in sorted(models.items()):
        scores = {r["record_id"]: r["score"] for r in entry["records"]}
        inner, outer = nested_ivap([scores[r] for r in ids_a], labels_a, fold_list)
        inner_by_model[model] = inner
        outer_by_model[model] = outer

    def combined_ba(members_by_index: Sequence[Sequence[str]], rule: str) -> dict[str, float]:
        def mix(values_by_model: Mapping[str, Any], index: int) -> float:
            return combine(
                [float(values_by_model[m][index]) for m in members_by_index[index]], rule
            )

        outer = [mix(outer_by_model, index) for index in range(len(ids_a))]
        inner = {}
        for fold in sorted(set(fold_list)):
            per_model = {m: inner_by_model[m][fold] for m in inner_by_model}
            inner[fold] = [
                mix(per_model, index) if fold_list[index] != fold else math.nan
                for index in range(len(ids_a))
            ]
        return _nested_threshold_ba(cohorts_a, labels_a, fold_list, inner, outer)

    comparator_ba = combined_ba([[comparator]] * len(ids_a), "E3a")
    configurations: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []

    for config_id, members in sorted(eligibility["configurations"].items()):
        absent = sorted(set(members) - set(models))
        if absent:
            configurations[config_id] = {
                "members": members,
                "status": "not_evaluable_members_absent_from_cache",
                "absent_members": absent,
            }
            continue
        common = [
            cohort
            for cohort in eligibility["cohorts"]
            if _eligible(eligibility, comparator, cohort)
        ]
        effective = {
            cohort: [m for m in members if _eligible(eligibility, m, cohort)] for cohort in common
        }
        degenerate = sorted(c for c, ms in effective.items() if ms == [comparator])
        entry: dict[str, Any] = {
            "members": members,
            "status": "evaluated",
            "common_cohorts": common,
            "effective_members_by_cohort": effective,
            "degenerate_cohorts": degenerate,
            "rules": {},
        }
        members_by_index = [effective.get(cohort) or [comparator] for cohort in cohorts_a]
        cost = configuration_cost(members)
        entry["cost_measured"] = cost
        for rule in RULES:
            ba = combined_ba(members_by_index, rule)
            differences = [ba[c] - comparator_ba[c] for c in common]
            ensemble_macro = sum(ba[c] for c in common) / len(common)
            comparator_macro = sum(comparator_ba[c] for c in common) / len(common)
            gain = ensemble_macro - comparator_macro
            result = {
                "ba_by_cohort": {c: ba[c] for c in common},
                "macro_ba": ensemble_macro,
                "comparator_macro_ba": comparator_macro,
                "gain_vs_comparator": gain,
                "meets_replacement_margin": gain >= REPLACEMENT_MARGIN,
                "bootstrap": _paired_bootstrap(differences),
            }
            entry["rules"][rule] = result
            candidates.append(
                {
                    "configuration": f"{rule}-{config_id}",
                    "members": len(members),
                    "cost": cost,
                    **result,
                }
            )
        configurations[config_id] = entry

    qualifying = [c for c in candidates if c["meets_replacement_margin"]]
    decision: dict[str, Any] = {"replacement_margin": REPLACEMENT_MARGIN}
    if not qualifying:
        decision.update({"outcome": "factcg_remains_baseline", "selected": None})
    else:
        best = max(c["macro_ba"] for c in qualifying)
        tied = [c for c in qualifying if best - c["macro_ba"] < REPLACEMENT_MARGIN]
        tied.sort(key=_tie_break_key)
        decision.update(
            {
                "outcome": "ensemble_replaces_factcg",
                "selected": tied[0]["configuration"],
                "tie_break": "lowest measured cost, then fewest members",
                "tied_candidates": [
                    {
                        "configuration": c["configuration"],
                        "cost_measured": c["cost"],
                        "members": c["members"],
                        "macro_ba": c["macro_ba"],
                    }
                    for c in tied
                ],
            }
        )

    report: dict[str, Any] = {
        "schema_version": "phase1b-dev-e3-ensemble-v1",
        "split": "dev",
        "partition": "DEV-A cross-fitted",
        "experiment": "e3-fixed-rule-ensemble",
        "classification": eligibility["status"],
        "preregistration": "docs/benchmarks/PREREG-E3-ENSEMBLE-v0.8.md",
        "preregistration_approved_on": approved_on,
        "cross_fitting": "nested: inner IVAP out-of-fold for thresholds, outer IVAP for evaluation",
        "cost_source": "MODEL_COST_SECONDS (Calibration V2 measured cost per member)",
        "decision_record": "DEC-024 option B",
        "eligibility_sha256": sha256_bytes(canonical_json(dict(eligibility))),
        "source_run_id": cache["source_run_id"],
        "manifest_sha256": cache["manifest_sha256"],
        "record_count": cache["record_count"],
        "dev_a_count": len(ids_a),
        "models_in_cache": sorted(models),
        "comparator": comparator,
        "comparator_pipeline": "same nested IVAP + per-cohort threshold pipeline as the ensembles",
        "comparator_ba_by_cohort": comparator_ba,
        "clip": CLIP,
        "configurations": configurations,
        "decision": decision,
        "instance_level_output_published": False,
    }
    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report
