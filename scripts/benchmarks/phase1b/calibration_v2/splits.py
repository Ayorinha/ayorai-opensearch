"""Version-independent deterministic DEV partitioning and cross-fitting folds."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence

from scripts.benchmarks.phase1b.common import canonical_json

DEV_SPLIT_SEED = "20261106"
CROSSFIT_SEED = "20261107"
N_FOLDS = 5


def _validate_inputs(
    record_ids: Sequence[str], cohorts: Sequence[str], labels: Sequence[str | int] | None = None
) -> None:
    if not record_ids or len(record_ids) != len(cohorts):
        raise ValueError("record_ids and cohorts must be non-empty and equally sized")
    if any(not isinstance(value, str) or not value for value in record_ids):
        raise ValueError("record_ids must be non-empty strings")
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("record_ids must be unique")
    if any(not isinstance(value, str) or not value for value in cohorts):
        raise ValueError("cohorts must be non-empty strings")
    if labels is not None:
        if len(labels) != len(record_ids):
            raise ValueError("labels must have the same length as record_ids")
        if any(
            isinstance(value, bool) or not isinstance(value, (str, int)) or value == ""
            for value in labels
        ):
            raise ValueError("labels must be non-empty strings or integers")


def _digest_key(seed: str, *parts: str) -> str:
    payload = "|".join((seed, *parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def split_dev_a_b(
    record_ids: Sequence[str], cohorts: Sequence[str]
) -> tuple[dict[str, str], str]:
    """Assign DEV-A/DEV-B by seeded SHA-256 ordering; return mapping and its SHA-256."""
    _validate_inputs(record_ids, cohorts)
    grouped: dict[str, list[str]] = defaultdict(list)
    for record_id, cohort in zip(record_ids, cohorts, strict=True):
        grouped[cohort].append(record_id)

    assignment: dict[str, str] = {}
    for cohort in sorted(grouped):
        ordered = sorted(
            grouped[cohort],
            key=lambda record_id: (
                _digest_key(DEV_SPLIT_SEED, cohort, record_id),
                record_id,
            ),
        )
        midpoint = (len(ordered) + 1) // 2
        assignment.update({record_id: "DEV-A" for record_id in ordered[:midpoint]})
        assignment.update({record_id: "DEV-B" for record_id in ordered[midpoint:]})

    canonical_mapping = {record_id: assignment[record_id] for record_id in sorted(assignment)}
    mapping_sha256 = hashlib.sha256(canonical_json(canonical_mapping)).hexdigest()
    return canonical_mapping, mapping_sha256


def crossfit_folds(
    record_ids: Sequence[str], cohorts: Sequence[str], labels: Sequence[str | int]
) -> tuple[dict[str, int], list[dict[str, str | int]]]:
    """Assign five folds by seeded SHA-256 ordering and report undersized strata."""
    _validate_inputs(record_ids, cohorts, labels)
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record_id, cohort, label in zip(record_ids, cohorts, labels, strict=True):
        grouped[(cohort, str(label))].append(record_id)

    folds: dict[str, int] = {}
    limitations: list[dict[str, str | int]] = []
    for cohort, label in sorted(grouped):
        ordered = sorted(
            grouped[(cohort, label)],
            key=lambda record_id: (
                _digest_key(CROSSFIT_SEED, cohort, label, record_id),
                record_id,
            ),
        )
        if len(ordered) < N_FOLDS:
            limitations.append(
                {"cohort": cohort, "label": label, "n": len(ordered), "required_folds": N_FOLDS}
            )
        for position, record_id in enumerate(ordered):
            folds[record_id] = position % N_FOLDS

    return {record_id: folds[record_id] for record_id in sorted(folds)}, limitations
