"""Compute human inter-annotator agreement; never annotate or execute the system."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # run as a script: make the repository importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.ptbr.rgc_random import LABEL_CASE_KAPPA, RGC_SEED, RgcPrng, percentile_ci95  # noqa: E402

VOCABULARY = (
    "SUPPORTED",
    "REFUTED",
    "UNVERIFIED",
    "PARTIALLY_SUPPORTED",
    "CONFLICTING",
)
RULE_GAP = "RULE_GAP"
ALLOWED_LABELS = frozenset((*VOCABULARY, RULE_GAP))
DEFAULT_ITERATIONS = 10_000
DEFAULT_SEED = RGC_SEED
GATE_THRESHOLD = 0.6


def _load_annotations_bytes(content: bytes, source: Path) -> dict[str, str]:
    """Parse strict JSONL from an immutable byte snapshot."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source}: annotation file must be UTF-8") from exc

    annotations: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{source}:{line_number}: blank lines are not allowed")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict) or set(row) != {"case_id", "label"}:
            raise ValueError(f"{source}:{line_number}: expected exactly case_id and label")
        case_id, label = row["case_id"], row["label"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{source}:{line_number}: case_id must be a non-empty string")
        if case_id in annotations:
            raise ValueError(f"{source}:{line_number}: duplicate case_id {case_id!r}")
        if not isinstance(label, str) or label not in ALLOWED_LABELS:
            raise ValueError(f"{source}:{line_number}: invalid label {label!r}")
        annotations[case_id] = label
    if not annotations:
        raise ValueError(f"{source}: annotation file is empty")
    return annotations


def load_annotations(path: Path) -> dict[str, str]:
    """Load strict JSONL annotations from one byte snapshot of the file."""
    return _load_annotations_bytes(path.read_bytes(), path)


def _cohen_kappa(
    labels_a: Sequence[str], labels_b: Sequence[str]
) -> tuple[float | None, float, dict[str, dict[str, int]]]:
    if len(labels_a) != len(labels_b):
        raise ValueError("annotation vectors must have equal lengths")
    if not labels_a:
        raise ValueError("kappa requires at least one eligible case")
    matrix = {a: {b: 0 for b in VOCABULARY} for a in VOCABULARY}
    for label_a, label_b in zip(labels_a, labels_b, strict=True):
        matrix[label_a][label_b] += 1
    n = len(labels_a)
    observed = sum(matrix[label][label] for label in VOCABULARY) / n
    row_marginals = {label: sum(matrix[label].values()) for label in VOCABULARY}
    column_marginals = {
        label: sum(matrix[row][label] for row in VOCABULARY) for label in VOCABULARY
    }
    expected = sum(row_marginals[label] * column_marginals[label] for label in VOCABULARY) / (n * n)
    denominator = 1.0 - expected
    if abs(denominator) <= 1e-12:
        return None, observed, matrix
    return (observed - expected) / denominator, observed, matrix


def compute_agreement(
    annotations_a: Mapping[str, str],
    annotations_b: Mapping[str, str],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Report unweighted Cohen's kappa; RULE_GAP pairs are excluded by prior rule."""
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be positive")
    ids_a, ids_b = set(annotations_a), set(annotations_b)
    if ids_a != ids_b:
        raise ValueError(
            "annotation case IDs differ: "
            f"only in A={sorted(ids_a - ids_b)}, only in B={sorted(ids_b - ids_a)}"
        )
    for annotator, labels in (("A", annotations_a), ("B", annotations_b)):
        invalid = sorted(
            (case_id, label)
            for case_id, label in labels.items()
            if not isinstance(label, str) or label not in ALLOWED_LABELS
        )
        if invalid:
            raise ValueError(f"annotator {annotator} has invalid labels: {invalid}")

    case_ids = sorted(ids_a)
    excluded_ids = [
        case_id
        for case_id in case_ids
        if annotations_a[case_id] == RULE_GAP or annotations_b[case_id] == RULE_GAP
    ]
    eligible_ids = [case_id for case_id in case_ids if case_id not in set(excluded_ids)]
    if not eligible_ids:
        raise ValueError("no eligible cases remain after excluding RULE_GAP pairs")

    labels_a = [annotations_a[case_id] for case_id in eligible_ids]
    labels_b = [annotations_b[case_id] for case_id in eligible_ids]
    kappa, observed, matrix = _cohen_kappa(labels_a, labels_b)

    rng = RgcPrng(seed, LABEL_CASE_KAPPA)
    bootstrap_values: list[float] = []
    degenerate_replicates = 0
    n = len(eligible_ids)
    for _ in range(iterations):
        indices = [rng.below(n) for _ in range(n)]
        sample_a = [labels_a[index] for index in indices]
        sample_b = [labels_b[index] for index in indices]
        sample_kappa, _, _ = _cohen_kappa(sample_a, sample_b)
        if sample_kappa is None:
            degenerate_replicates += 1
        else:
            bootstrap_values.append(sample_kappa)

    ci95 = percentile_ci95(bootstrap_values)

    class_distribution = {
        label: {
            "annotator_a": labels_a.count(label),
            "annotator_b": labels_b.count(label),
            "agreements": matrix[label][label],
        }
        for label in VOCABULARY
    }
    excluded_disagreements = sum(
        annotations_a[case_id] != annotations_b[case_id] for case_id in excluded_ids
    )
    return {
        "method": "cohen_kappa_unweighted",
        "n_eligible": n,
        "n_rule_gap_excluded": len(excluded_ids),
        "rule_gap_excluded_disagreements": excluded_disagreements,
        "cohen_kappa": round(kappa, 6) if kappa is not None else None,
        "gate_threshold": GATE_THRESHOLD,
        "gate_passed": kappa is not None and kappa >= GATE_THRESHOLD,
        "observed_agreement": round(observed, 6),
        "ci95_case_bootstrap": ([round(value, 6) for value in ci95] if ci95 is not None else None),
        "bootstrap": {
            "method": "percentile_case_bootstrap",
            "iterations": iterations,
            "seed": seed,
            "generator": "RGC-PRNG-1",
            "percentile": "hyndman-fan-type-7",
            "valid_replicates": len(bootstrap_values),
            "degenerate_replicates": degenerate_replicates,
        },
        "confusion_matrix": matrix,
        "class_distribution": class_distribution,
        "rule_gap_excluded_case_ids": excluded_ids,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation-a", type=Path, required=True)
    parser.add_argument("--annotation-b", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    # The protocol-facing CLI always uses DEC-020/DEC-027 canonical parameters.
    # Custom values remain available through the Python API for isolated tests/diagnostics.
    # Read each input exactly once. Parsing, agreement, and provenance hashes
    # must all refer to the same bytes even if a path changes during execution.
    annotation_a_bytes = args.annotation_a.read_bytes()
    annotation_b_bytes = args.annotation_b.read_bytes()
    result = compute_agreement(
        _load_annotations_bytes(annotation_a_bytes, args.annotation_a),
        _load_annotations_bytes(annotation_b_bytes, args.annotation_b),
    )
    result["inputs"] = {
        "annotation_a_sha256": hashlib.sha256(annotation_a_bytes).hexdigest(),
        "annotation_b_sha256": hashlib.sha256(annotation_b_bytes).hexdigest(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"n={result['n_eligible']} kappa={result['cohen_kappa']} "
        f"gate_passed={result['gate_passed']} out={args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
