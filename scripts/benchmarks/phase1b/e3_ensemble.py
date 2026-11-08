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
passed through the identical pipeline (IVAP out-of-fold probabilities, then cross-fitted
per-cohort thresholds). Both arms share the same probability step, so the comparison
is like-for-like. The Calibration V2 Layer 1 FactCG value (raw-score thresholds) is
reported alongside for reference. Known limitation, shared by both arms: an out-of-fold
probability for a record in fold j comes from a calibrator fitted on the other folds,
including the fold later used for evaluation of a different record; thresholds are
still chosen only on training folds.

DEV-B and TEST are never used. Output is aggregate-only.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.benchmarks.phase1b.calibration_v2.aggregate import _crossfit_threshold_ba
from scripts.benchmarks.phase1b.calibration_v2.splits import crossfit_folds, split_dev_a_b
from scripts.benchmarks.phase1b.calibration_v2.venn_abers import ivap_crossfit
from scripts.benchmarks.phase1b.common import canonical_json, sha256_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ELIGIBILITY_PATH = REPOSITORY_ROOT / "configs" / "benchmarks" / "e3-eligibility-v0.8.json"
PREREGISTRATION_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-ENSEMBLE-v0.8.md"
CLIP = 1e-6
REPLACEMENT_MARGIN = 0.005
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261108
RULES = ("E3a", "E3b")


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
    if eligibility.get("schema_version") != "phase1b-e3-eligibility-v1":
        raise ValueError("unsupported E3 eligibility file")
    cohorts = set(eligibility["cohorts"])
    for member, entry in eligibility["members"].items():
        unknown = set(entry["blocked_cohorts"]) - cohorts
        if unknown:
            raise ValueError(f"{member} blocks unknown cohorts: {sorted(unknown)}")
    for config_id, members in eligibility["configurations"].items():
        if eligibility["comparator"] not in members:
            raise ValueError(f"configuration {config_id} must contain the comparator")
        missing = set(members) - set(eligibility["members"])
        if missing:
            raise ValueError(f"configuration {config_id} has unknown members: {sorted(missing)}")
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


def run_e3(cache: Mapping[str, Any], eligibility: Mapping[str, Any] | None = None) -> dict:
    """Evaluate every preregistered configuration and rule that the cache supports."""

    if not PREREGISTRATION_PATH.is_file():
        raise RuntimeError("E3 preregistration is not on this revision; refusing to run")
    eligibility = eligibility if eligibility is not None else load_eligibility()
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

    probabilities: dict[str, list[float]] = {}
    for model, entry in sorted(models.items()):
        scores = {r["record_id"]: r["score"] for r in entry["records"]}
        result = ivap_crossfit([scores[r] for r in ids_a], labels_a, fold_list)
        probabilities[model] = [float(value) for value in result["p"]]

    def crossfit_ba(values: Sequence[float]) -> dict[str, float]:
        return _crossfit_threshold_ba(ids_a, cohorts_a, labels_a, values, range(len(ids_a)))

    comparator_ba = crossfit_ba(probabilities[comparator])
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
        for rule in RULES:
            combined = [
                combine(
                    [probabilities[m][index] for m in effective.get(cohorts_a[index], [])]
                    or [probabilities[comparator][index]],
                    rule,
                )
                for index in range(len(ids_a))
            ]
            ba = crossfit_ba(combined)
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
                {"configuration": f"{rule}-{config_id}", "members": len(members), **result}
            )
        configurations[config_id] = entry

    qualifying = [c for c in candidates if c["meets_replacement_margin"]]
    decision: dict[str, Any] = {"replacement_margin": REPLACEMENT_MARGIN}
    if not qualifying:
        decision.update({"outcome": "factcg_remains_baseline", "selected": None})
    else:
        best = max(c["macro_ba"] for c in qualifying)
        tied = [c for c in qualifying if best - c["macro_ba"] < REPLACEMENT_MARGIN]
        tied.sort(key=lambda c: (c["members"], c["configuration"]))
        decision.update(
            {
                "outcome": "ensemble_replaces_factcg",
                "selected": tied[0]["configuration"],
                "tie_break": "fewest members (cost not measured per configuration)",
                "tied_candidates": [c["configuration"] for c in tied],
            }
        )

    report: dict[str, Any] = {
        "schema_version": "phase1b-dev-e3-ensemble-v1",
        "split": "dev",
        "partition": "DEV-A cross-fitted",
        "experiment": "e3-fixed-rule-ensemble",
        "classification": eligibility["status"],
        "preregistration": "docs/benchmarks/PREREG-E3-ENSEMBLE-v0.8.md",
        "decision_record": "DEC-024 option B",
        "eligibility_sha256": sha256_bytes(canonical_json(dict(eligibility))),
        "source_run_id": cache["source_run_id"],
        "manifest_sha256": cache["manifest_sha256"],
        "record_count": cache["record_count"],
        "dev_a_count": len(ids_a),
        "models_in_cache": sorted(models),
        "comparator": comparator,
        "comparator_pipeline": "IVAP out-of-fold probabilities + cross-fitted cohort thresholds",
        "comparator_ba_by_cohort": comparator_ba,
        "clip": CLIP,
        "configurations": configurations,
        "decision": decision,
        "instance_level_output_published": False,
    }
    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report
