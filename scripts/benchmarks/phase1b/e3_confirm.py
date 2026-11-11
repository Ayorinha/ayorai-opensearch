"""P1 — single confirmation of E3b-01 against FactCG on DEV-B (roadmap v0.8).

Implements docs/benchmarks/PREREG-E3-CONFIRM-DEV-B-v0.8.md under DEC-024 option B and
DEC-025:
- one hypothesis: E3b-01 (factcg + minicheck, mean of clipped logits) vs FactCG;
- IVAP calibrators fitted on all of DEV-A produce the DEV-B probabilities;
- per-cohort thresholds are chosen on DEV-A out-of-fold probabilities (Calibration V2
  folds) and applied once to DEV-B; no DEV-B label enters any fitted quantity;
- primary interval: paired bootstrap of DOCUMENT clusters within each cohort (whole
  documents resampled with replacement, same draws for both arms, BA recomputed per
  replicate), 2,000 replicates, PCG64(20261109); requires the v2 score cache (doc_id);
- diagnostics (no effect on the decision, exploratory, not inferential): document
  jackknife influence, record-level bootstrap, leave-one-cohort-out; secondary:
  cohort-cluster bootstrap;
- refuses to run until the objective rule for non-estimable cohorts is fixed by a
  dated amendment (NON_ESTIMABLE_RULE);
- CONFIRMED only if delta >= 0.005 and the primary 95% lower bound > 0.

Output is aggregate-only. TEST is never used.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
REQUIRED_CACHE_SCHEMA = "phase1b-dev-score-cache-v2"
# Fixed by a dated amendment after the cache v2 aggregate counts are published and before
# any DEV-B computation. Until then P1 refuses to run (fail-closed).
NON_ESTIMABLE_RULE: dict[str, Any] | None = None
# Single-execution lock (persistent part): a published P1 report in the repository.
REPORT_LOCK_GLOB = "reports/benchmarks/*p1-dev-b-confirmation*"
P1_LOCK_REF = "refs/heads/p1-dev-b-confirmation-lock"
ESTIMAND_STATEMENT = (
    "The estimand is the macro balanced accuracy over the common cohorts. No superiority "
    "claim is made for any individual cohort; per-cohort values are descriptive."
)


def published_confirmation_exists(root: Path | None = None) -> bool:
    """True when a P1 confirmation report is already published (execution is single-use)."""

    root = root if root is not None else REPOSITORY_ROOT
    return any(root.glob(REPORT_LOCK_GLOB))


def _validate_confirmatory_eligibility(
    eligibility: Mapping[str, Any], *, eligibility_sha256: str
) -> None:
    """Require a maintainer-approved DEC-026 exception for this exact P1 matrix."""

    authorization = eligibility.get("confirmatory_authorization")
    if not isinstance(authorization, Mapping):
        raise RuntimeError("DEC-026 has no approved P1 confirmatory authorization; refusing to run")
    if (
        authorization.get("decision") != "DEC-026"
        or authorization.get("status") != "approved"
        or authorization.get("scope") != "p1-dev-b-confirmatory"
    ):
        raise RuntimeError("DEC-026 does not explicitly approve this P1 scope")
    try:
        date.fromisoformat(str(authorization.get("approved_on", "")))
    except ValueError as exc:
        raise RuntimeError("DEC-026 P1 approval date is missing or invalid") from exc
    if authorization.get("eligibility_sha256") != eligibility_sha256:
        raise RuntimeError("DEC-026 approval does not bind the exact eligibility matrix")
    selection = authorization.get("selection_exposure")
    if not isinstance(selection, Mapping) or selection.get("status") != "resolved":
        raise RuntimeError("FactCG selection exposure is unresolved; P1 cannot be confirmatory")
    if not isinstance(selection.get("decision_ref"), str) or not selection["decision_ref"].strip():
        raise RuntimeError("the selection-exposure decision reference is missing")


def _require_non_estimable_rule() -> None:
    """Fail closed until an approved rule and its evaluator are implemented."""

    if NON_ESTIMABLE_RULE is None:
        raise RuntimeError(
            "the objective non-estimable-cohort amendment is not approved; P1 cannot run"
        )
    raise RuntimeError(
        "a non-null rule object is insufficient: its approved amendment and "
        "result-blind evaluator are not implemented; P1 cannot run"
    )


def _require_persistent_atomic_lock() -> None:
    """Atomically reserve the single-use P1 ref in GitHub before any DEV-B calculation.

    The protected workflow must provide a short-lived, repository-scoped P1_LOCK_TOKEN,
    GITHUB_ACTIONS, GITHUB_REPOSITORY and GITHUB_SHA. The ordinary GITHUB_TOKEN must
    remain read-only and is never accepted as a fallback. GitHub's create-ref endpoint is atomic: an
    existing reservation is a hard failure, including when it points to the same SHA.
    """
    repository = os.environ.get("GITHUB_REPOSITORY")
    commit_sha = os.environ.get("GITHUB_SHA")
    token = os.environ.pop("P1_LOCK_TOKEN", None)
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("P1 requires the protected GitHub Actions runner")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("P1 lock may only be reserved from the protected main branch")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("P1 lock requires an explicit workflow_dispatch event")
    if not re.fullmatch(r"[0-9]+", os.environ.get("GITHUB_RUN_ID", "")):
        raise RuntimeError("P1 lock requires a valid GitHub Actions run ID")
    if repository != "Ayorinha/ayorai-opensearch":
        raise RuntimeError("P1 lock may only be reserved in the canonical repository")
    if not isinstance(commit_sha, str) or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
        raise RuntimeError("P1 lock requires the exact 40-character workflow commit SHA")
    if not token:
        raise RuntimeError(
            "P1 lock requires a dedicated short-lived P1_LOCK_TOKEN; refusing GITHUB_TOKEN"
        )

    request = Request(
        f"https://api.github.com/repos/{repository}/git/refs",
        data=json.dumps({"ref": P1_LOCK_REF, "sha": commit_sha}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        # The URL is a fixed HTTPS GitHub API endpoint; no caller-controlled host is used.
        with urlopen(request, timeout=15) as response:  # nosec B310
            created = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {409, 422}:
            raise RuntimeError(
                "the persistent single-use P1 Git ref is already reserved; refusing to run"
            ) from exc
        raise RuntimeError(f"GitHub rejected the P1 lock reservation (HTTP {exc.code})") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("could not verify the persistent P1 lock reservation") from exc

    if (
        created.get("ref") != P1_LOCK_REF
        or not isinstance(created.get("object"), Mapping)
        or created["object"].get("type") != "commit"
        or created["object"].get("sha") != commit_sha
    ):
        raise RuntimeError("GitHub returned a mismatched P1 lock reference or commit SHA")


def validate_members(models: Mapping[str, Any]) -> list[str]:
    """Strict cross-member checks; returns the sorted record ids."""

    missing = [member for member in MEMBERS if member not in models]
    if missing:
        raise ValueError(f"the score cache lacks members: {missing}")
    reference: dict[str, tuple[str, str, str]] | None = None
    for member in MEMBERS:
        seen: dict[str, tuple[str, str, str]] = {}
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
            doc_id = record.get("doc_id")
            if not isinstance(doc_id, str) or re.fullmatch(r"[0-9a-f]{64}", doc_id) is None:
                raise ValueError(f"{member} lacks a valid doc_id (cache v2 required)")
            seen[record_id] = (record["cohort"], record["gold"], doc_id)
        if reference is None:
            reference = seen
        elif seen != reference:
            raise ValueError(
                f"{member} disagrees with {MEMBERS[0]} on records, cohorts, labels or documents"
            )
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


_STAT_COLUMNS = ("positives", "negatives", "ens_tp", "ens_tn", "cmp_tp", "cmp_tn")


def _document_stats(group: Mapping[str, Sequence[Any]]) -> tuple[list[str], Any]:
    """Per-document sufficient statistics for paired balanced accuracy."""

    import numpy as np

    documents = sorted(set(group["docs"]))
    position = {doc: index for index, doc in enumerate(documents)}
    stats = np.zeros((len(documents), len(_STAT_COLUMNS)), dtype=np.float64)
    for y, e, f, doc in zip(group["y"], group["e"], group["f"], group["docs"], strict=True):
        row = stats[position[doc]]
        if y == 1:
            row[0] += 1
            row[2] += e == 1
            row[4] += f == 1
        else:
            row[1] += 1
            row[3] += e == 0
            row[5] += f == 0
    return documents, stats


def _paired_ba_delta(totals: Any) -> tuple[Any, Any]:
    """BA(ensemble) - BA(comparator) from summed statistics; also an 'invalid' mask."""

    import numpy as np

    positives, negatives = totals[..., 0], totals[..., 1]
    invalid = (positives == 0) | (negatives == 0)
    safe_p = np.where(invalid, 1.0, positives)
    safe_n = np.where(invalid, 1.0, negatives)
    ens = (totals[..., 2] / safe_p + totals[..., 3] / safe_n) / 2.0
    cmp_ = (totals[..., 4] / safe_p + totals[..., 5] / safe_n) / 2.0
    return ens - cmp_, invalid


def _document_bootstrap(stats_by_cohort: Mapping[str, Any]) -> tuple[dict[str, Any], Any]:
    """Primary interval: resample whole documents within each cohort, paired arms."""

    import numpy as np

    rng = np.random.Generator(np.random.PCG64(STRATIFIED_SEED))
    differences = np.zeros(STRATIFIED_REPLICATES, dtype=np.float64)
    invalid = np.zeros(STRATIFIED_REPLICATES, dtype=bool)
    for cohort in sorted(stats_by_cohort):
        stats = stats_by_cohort[cohort]
        n_docs = stats.shape[0]
        draws = rng.integers(0, n_docs, size=(STRATIFIED_REPLICATES, n_docs))
        multiplicity = np.zeros((STRATIFIED_REPLICATES, n_docs), dtype=np.float64)
        for replicate in range(STRATIFIED_REPLICATES):
            multiplicity[replicate] = np.bincount(draws[replicate], minlength=n_docs)
        delta, bad = _paired_ba_delta(multiplicity @ stats)
        differences += delta
        invalid |= bad
    differences /= len(stats_by_cohort)
    valid = differences[~invalid]
    invalid_count = int(invalid.sum())
    estimable = invalid_count <= MAX_INVALID_FRACTION * STRATIFIED_REPLICATES and valid.size > 1
    low, high = (
        (float(v) for v in np.quantile(valid, [0.025, 0.975], method="linear"))
        if estimable
        else (None, None)
    )
    result = {
        "method": (
            "paired bootstrap of document clusters within each cohort "
            "(whole documents resampled with replacement; same draws for both arms)"
        ),
        "unit": "document (doc_id, scoped by cohort)",
        "replicates": STRATIFIED_REPLICATES,
        "invalid_replicates": invalid_count,
        "invalid_rule": "a replicate in which any cohort lacks a class is invalid",
        "estimable": bool(estimable),
        "generator": f"numpy.random.Generator(PCG64({STRATIFIED_SEED}))",
        "numpy_version": np.__version__,
        "quantile_method": "linear",
        "ci95_difference": [low, high],
    }
    return result, valid


def _document_jackknife(stats_by_cohort: Mapping[str, Any], delta: float) -> dict[str, Any]:
    """Exploratory influence diagnostic, NOT an inferential jackknife.

    Each document is removed in turn and the macro delta recomputed. Removals that leave
    a cohort without a class are skipped, and removals from cohorts of different sizes are
    pooled, so this is not a standard stratified jackknife; it only shows how much a
    single document can move the estimate.
    """

    import numpy as np

    cohorts = sorted(stats_by_cohort)
    per_cohort = {c: float(_paired_ba_delta(stats_by_cohort[c].sum(axis=0))[0]) for c in cohorts}
    total = sum(per_cohort.values())
    values: list[float] = []
    skipped = 0
    for cohort in cohorts:
        stats = stats_by_cohort[cohort]
        reduced = stats.sum(axis=0) - stats
        cohort_delta, bad = _paired_ba_delta(reduced)
        skipped += int(bad.sum())
        for value in cohort_delta[~bad]:
            values.append((total - per_cohort[cohort] + float(value)) / len(cohorts))
    array = np.asarray(values, dtype=np.float64)
    n = array.size
    se = float(np.sqrt((n - 1) / n * np.sum((array - array.mean()) ** 2))) if n > 1 else None
    return {
        "role": "exploratory influence diagnostic; not inferential; no effect on the decision",
        "documents_used": int(n),
        "documents_skipped_class_missing": skipped,
        "pooled_jackknife_se_not_inferential": se,
        "max_abs_influence": float(np.max(np.abs(array - delta))) if n else None,
        "values": array,
    }


def preflight_confirm() -> tuple[str, dict[str, Any], str]:
    """Validate every public P1 gate before any encrypted score cache is accessed."""

    approved_on = preregistration_approval(PREREGISTRATION_PATH)
    file_sha256 = sha256_bytes(Path(ELIGIBILITY_PATH).read_bytes())
    if file_sha256 != ELIGIBILITY_SHA256:
        raise RuntimeError("eligibility file differs from the preregistered version")
    eligibility = load_eligibility()
    _validate_eligibility(eligibility)
    _validate_confirmatory_eligibility(eligibility, eligibility_sha256=file_sha256)
    _require_non_estimable_rule()
    return approved_on, eligibility, file_sha256


def run_confirm(cache: Mapping[str, Any]) -> dict:
    """Single execution of P1; the only eligibility accepted is the preregistered file."""

    approved_on, eligibility, file_sha256 = preflight_confirm()
    if cache.get("schema_version") != REQUIRED_CACHE_SCHEMA:
        raise ValueError("P1 requires the v2 score cache with document ids")
    models = cache["models"]
    record_ids = validate_members(models)
    reference = {r["record_id"]: r for r in models[COMPARATOR]["records"]}
    cohorts = [reference[r]["cohort"] for r in record_ids]
    doc_ids = [reference[r]["doc_id"] for r in record_ids]

    common = [c for c in eligibility["cohorts"] if _eligible(eligibility, COMPARATOR, c)]
    for cohort in common:
        if not all(_eligible(eligibility, member, cohort) for member in MEMBERS):
            raise ValueError(f"a member is blocked in common cohort {cohort}")
    if not common:
        raise ValueError("the confirmatory eligibility matrix has no common cohorts")
    common_set = set(common)

    # Complete deterministic preflight before consuming the one-shot reservation.
    # DEV-B labels are checked only for schema/cross-member consistency here; they are
    # not used as outcomes, fitted quantities, scores, or diagnostics before reservation.
    assignments, _ = split_dev_a_b(record_ids, cohorts)
    index_a = [i for i, r in enumerate(record_ids) if assignments[r] == "DEV-A"]
    index_b = [i for i, r in enumerate(record_ids) if assignments[r] == "DEV-B"]
    if not index_a or not index_b:
        raise ValueError("the deterministic DEV-A/DEV-B split is empty")
    ids_a = [record_ids[i] for i in index_a]
    cohorts_a = [cohorts[i] for i in index_a]
    labels_a = [1 if reference[record_ids[i]]["gold"] == "SUPPORTED" else 0 for i in index_a]
    folds, limitations = crossfit_folds(ids_a, cohorts_a, labels_a)
    if limitations:
        raise ValueError("DEV-A has cross-fitting strata below five")
    fold_list = [folds[r] for r in ids_a]

    # Check the report-level guard and reserve only after all deterministic preflight.
    # An existing report or invalid cache must not consume a fresh reservation.
    if published_confirmation_exists():
        raise RuntimeError("a P1 confirmation report is already published; P1 is single-use")
    _require_persistent_atomic_lock()

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

    labels_b = [
        1 if reference[record_ids[index_b[k]]]["gold"] == "SUPPORTED" else 0 for k in keep_b
    ]
    cohorts_b = [cohorts[index_b[k]] for k in keep_b]
    docs_b = [doc_ids[index_b[k]] for k in keep_b]
    groups: dict[str, tuple[list[int], list[int], list[int]]] = {}
    stats_by_cohort: dict[str, Any] = {}
    documents_by_cohort: dict[str, int] = {}
    ba_by_arm: dict[str, dict[str, float]] = {"ensemble": {}, "comparator": {}}
    counts: dict[str, int] = {}
    for cohort in common:
        members_idx = [j for j, c in enumerate(cohorts_b) if c == cohort]
        if not members_idx:
            raise ValueError(f"common cohort {cohort} has no DEV-B records")
        y = [labels_b[j] for j in members_idx]
        if len(set(y)) < 2:
            raise ValueError(f"cohort {cohort} lacks a class in DEV-B; BA is undefined")
        e = [predictions["ensemble"][j] for j in members_idx]
        f = [predictions["comparator"][j] for j in members_idx]
        groups[cohort] = (y, e, f)
        counts[cohort] = len(members_idx)
        _, stats_by_cohort[cohort] = _document_stats(
            {"y": y, "e": e, "f": f, "docs": [docs_b[j] for j in members_idx]}
        )
        documents_by_cohort[cohort] = int(stats_by_cohort[cohort].shape[0])
        ba_by_arm["ensemble"][cohort] = balanced_accuracy(y, e)
        ba_by_arm["comparator"][cohort] = balanced_accuracy(y, f)

    macro_e = sum(ba_by_arm["ensemble"].values()) / len(common)
    macro_c = sum(ba_by_arm["comparator"].values()) / len(common)
    delta = macro_e - macro_c
    primary, _ = _document_bootstrap(stats_by_cohort)
    jackknife = _document_jackknife(stats_by_cohort, delta)
    jackknife.pop("values")
    case_bootstrap = _stratified_bootstrap(groups)
    secondary = _paired_bootstrap(
        [ba_by_arm["ensemble"][c] - ba_by_arm["comparator"][c] for c in common]
    )
    low, high = primary["ci95_difference"]
    confirmed = primary["estimable"] and delta >= REPLACEMENT_MARGIN and low > 0
    outcome = "CONFIRMED" if confirmed else "NOT_CONFIRMED"
    contrary = bool(primary["estimable"] and high is not None and high < 0)

    partition_label = " ".join(
        (
            "conditional confirmation on partially used holdout",
            "(DEV-B; calibrated on DEV-A)",
        )
    )
    confirmation_label = " ".join(
        (
            "confirmação condicional em holdout parcialmente usado",
            "(DEV-B)",
        )
    )
    report: dict[str, Any] = {
        "schema_version": "phase1b-dev-e3-confirm-v2",
        "split": "dev",
        "partition": partition_label,
        "confirmation_classification": confirmation_label,
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
        "dev_b_documents_by_cohort": documents_by_cohort,
        "non_estimable_rule": NON_ESTIMABLE_RULE,
        "diagnostics": {
            "role": "exploratory; not inferential; no effect on the decision",
            "document_influence": jackknife,
            "record_level_bootstrap": case_bootstrap,
        },
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
