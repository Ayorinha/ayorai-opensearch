"""Local-only LLM-AggreFact component evaluation; no dataset download."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from ayorai_attractor.evaluation.stats import bootstrap_accuracy
from ayorai_attractor.verification.extraction import (
    ComponentProvenance,
    ExtractedClaim,
    RetrievedDocument,
)
from ayorai_attractor.verification.models import Claim, Stance
from ayorai_attractor.verification.stance import RuleStanceDetector

SCHEMA_VERSION = "1.0.0"
SEED = 20261003
ITERATIONS = 10000
MAX_FAILURE_RATE = 0.01
RAGTRUTH_COHORTS = {"ragtruth", "rag-truth"}


class DatasetError(ValueError):
    """Invalid dataset schema or mapping."""


class EvaluatedRow(TypedDict):
    record_index: int
    dataset: str
    gold: str
    prediction: str
    stance: str


def sha256_file(path: Path) -> str:
    """Compute SHA-256 incrementally for a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read local JSONL, CSV, or Parquet only."""
    if not path.is_file():
        raise DatasetError("dataset path is not a file")
    suffix = path.suffix.lower()
    required = {"doc", "claim", "label", "dataset"}
    if suffix in {".jsonl", ".ndjson"}:
        records = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"invalid JSONL at line {line_number}") from exc
            if not isinstance(item, dict):
                raise DatasetError(f"line {line_number} must contain an object")
            records.append(item)
        return records
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise DatasetError("CSV schema must contain doc, claim, label, dataset")
            return list(reader)
    if suffix in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as parquet  # type: ignore[import-untyped]
        except ImportError as exc:
            raise DatasetError("Parquet input requires pyarrow") from exc
        table = parquet.read_table(path)
        if not required.issubset(table.column_names):
            raise DatasetError("Parquet schema must contain doc, claim, label, dataset")
        return cast(list[dict[str, Any]], table.to_pylist())
    raise DatasetError("supported formats: JSONL, CSV, Parquet")


def load_mapping(path: Path) -> dict[str, Any]:
    """Load and validate the versioned native binary label mapping."""
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetError("invalid mapping JSON") from exc
    if not isinstance(mapping, dict):
        raise DatasetError("mapping JSON must contain an object")
    if mapping.get("schema_version") != SCHEMA_VERSION:
        raise DatasetError("unsupported mapping schema version")
    if mapping.get("mapping_id") != "llm-aggrefact-label-map-v1":
        raise DatasetError("unsupported mapping ID")
    expected = {"1": "SUPPORTED", "0": "NOT_SUPPORTED"}
    if mapping.get("native_binary_labels") != expected:
        raise DatasetError("label mapping differs from documented mapping")
    return mapping


def adapt_records(
    records: list[dict[str, Any]], mapping: dict[str, Any]
) -> list[dict[str, str]]:
    """Validate file schema and adapt the native binary labels."""
    required = {"doc", "claim", "label", "dataset"}
    if not records:
        raise DatasetError("dataset is empty")
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not required.issubset(record):
            raise DatasetError(f"record {index}: invalid dataset schema")
    adapted = []
    labels = mapping["native_binary_labels"]
    for index, record in enumerate(records):
        doc, claim, cohort = record["doc"], record["claim"], record["dataset"]
        if not isinstance(doc, str) or not doc.strip():
            raise DatasetError(f"record {index}: doc must be nonempty string")
        if not isinstance(claim, str) or not claim.strip():
            raise DatasetError(f"record {index}: claim must be nonempty string")
        if not isinstance(cohort, str) or not cohort.strip():
            raise DatasetError(
                f"record {index}: dataset cohort must be nonempty string"
            )
        label = labels.get(str(record["label"]))
        if label not in {"SUPPORTED", "NOT_SUPPORTED"}:
            raise DatasetError(f"record {index}: unknown label")
        adapted.append(
            {
                "doc": doc,
                "claim": claim,
                "label": label,
                "dataset": cohort.strip(),
                "record_id": str(index),
            }
        )
    return adapted


def predict(row: dict[str, str], detector: RuleStanceDetector) -> tuple[str, str]:
    """Run stance detector only, without Judge 2.0 or the full pipeline."""
    claim = Claim(id="claim-1", text=row["claim"])
    claim_hash = hashlib.sha256(row["claim"].encode("utf-8")).hexdigest()
    extracted = ExtractedClaim(
        claim=claim,
        confidence=1.0,
        provenance=ComponentProvenance(
            "benchmark-adapter", "local-fixture", "1", claim_hash, claim_hash
        ),
    )
    document = RetrievedDocument(
        id="evidence-1",
        content=row["doc"],
        source_id="local-dataset",
        source_location="local-record:" + row["record_id"],
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        origin_id="local-dataset",
        end_offset=len(row["doc"]),
    )
    detected = detector.detect([extracted], [document.to_evidence("claim-1")])
    if len(detected.edges) != 1:
        raise RuntimeError("detector output cardinality mismatch")
    stance = detected.edges[0].edge.stance
    prediction = "SUPPORTED" if stance is Stance.SUPPORTS else "NOT_SUPPORTED"
    return prediction, stance.value.upper()


def metrics(gold: list[str], predicted: list[str]) -> dict[str, Any]:
    """Compute binary classification metrics."""
    if not gold or len(gold) != len(predicted):
        raise ValueError("metrics require nonempty equal-length arrays")
    labels = ("SUPPORTED", "NOT_SUPPORTED")
    matrix = {label: {guess: 0 for guess in labels} for label in labels}
    for actual, guess in zip(gold, predicted, strict=True):
        matrix[actual][guess] += 1
    per_class = {}
    recalls = []
    for label in labels:
        tp = matrix[label][label]
        fn = sum(matrix[label][other] for other in labels if other != label)
        fp = sum(matrix[other][label] for other in labels if other != label)
        support = tp + fn
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        if support:
            recalls.append(recall)
    accuracy = sum(a == b for a, b in zip(gold, predicted, strict=True)) / len(gold)
    counts = Counter(gold)
    majority, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return {
        "n": len(gold),
        "balanced_accuracy": sum(recalls) / len(recalls),
        "accuracy": accuracy,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "majority_baseline": {"label": majority, "accuracy": count / len(gold)},
    }


def bootstrap_balanced_accuracy(
    gold: list[str], predicted: list[str], *, iterations: int, seed: int
) -> tuple[float, float]:
    """Bootstrap claim-document rows; source/document dependence may narrow CI."""
    rng = random.Random(seed)  # nosec B311 - seeded statistical resampling
    values = []
    for _ in range(iterations):
        indices = [rng.randrange(len(gold)) for _ in gold]
        sample_gold = [gold[index] for index in indices]
        sample_pred = [predicted[index] for index in indices]
        values.append(metrics(sample_gold, sample_pred)["balanced_accuracy"])
    values.sort()
    lower = values[int(0.025 * (iterations - 1))]
    upper = values[int(0.975 * (iterations - 1))]
    return lower, upper


def evaluate(
    dataset: Path,
    mapping_path: Path,
    out_json: Path,
    out_md: Path,
    *,
    code_sha: str,
) -> dict[str, Any]:
    """Evaluate a local file and write aggregate-only reports."""
    if not code_sha.strip():
        raise ValueError("--code-sha must be a nonempty value")
    mapping = load_mapping(mapping_path)
    rows = adapt_records(read_records(dataset), mapping)
    detector = RuleStanceDetector()
    evaluated: list[EvaluatedRow] = []
    failures: Counter[str] = Counter()
    failure_indices: dict[str, list[int]] = {}
    for row in rows:
        try:
            prediction, stance = predict(row, detector)
            evaluated.append(
                {
                    "record_index": int(row["record_id"]),
                    "dataset": row["dataset"],
                    "gold": row["label"],
                    "prediction": prediction,
                    "stance": stance,
                }
            )
        except Exception as exc:
            error_type = type(exc).__name__
            failures[error_type] += 1
            failure_indices.setdefault(error_type, []).append(int(row["record_id"]))
    n_total = len(rows)
    n_failures = sum(failures.values())
    if n_failures / n_total > MAX_FAILURE_RATE:
        raise RuntimeError(
            f"record failure rate {n_failures}/{n_total} exceeds 1%; "
            f"types={dict(failures)}"
        )
    if not evaluated:
        raise RuntimeError("no records evaluated successfully")
    gold = [item["gold"] for item in evaluated]
    predicted = [item["prediction"] for item in evaluated]
    overall = metrics(gold, predicted)
    balanced_ci = bootstrap_balanced_accuracy(
        gold, predicted, iterations=ITERATIONS, seed=SEED
    )
    accuracy_ci = bootstrap_accuracy(
        gold, predicted, iterations=ITERATIONS, seed=SEED + 1
    )
    cohorts = {}
    for cohort in sorted({item["dataset"] for item in evaluated}):
        group = [item for item in evaluated if item["dataset"] == cohort]
        cohorts[cohort] = metrics(
            [item["gold"] for item in group],
            [item["prediction"] for item in group],
        )
    rag_names = {name.casefold() for name in RAGTRUTH_COHORTS}
    without_ragtruth = [
        item for item in evaluated if item["dataset"].casefold() not in rag_names
    ]
    if not without_ragtruth:
        raise DatasetError("RAGTruth-excluded cohort is empty")
    no_rag_metrics = metrics(
        [item["gold"] for item in without_ragtruth],
        [item["prediction"] for item in without_ragtruth],
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "dataset": "LLM-AggreFact",
        "mapping_id": mapping["mapping_id"],
        "task": "binary_claim_document_support",
        "evaluated_component": "RuleStanceDetector (stance only, sem Judge 2.0)",
        "end_to_end_attractor": False,
        "primary_metric": "balanced_accuracy",
        "metrics": overall,
        "bootstrap_ci95_balanced_accuracy": {
            "lower": balanced_ci[0],
            "upper": balanced_ci[1],
            "iterations": ITERATIONS,
            "seed": SEED,
            "unit": "claim-document row sampled with replacement",
            "clustered": False,
            "limitation": (
                "row-level CI may be optimistic due to source/document dependence"
            ),
        },
        "bootstrap_ci95_accuracy": {
            "lower": accuracy_ci[0],
            "upper": accuracy_ci[1],
            "iterations": ITERATIONS,
            "seed": SEED + 1,
            "unit": "claim-document row sampled with replacement",
            "clustered": False,
            "limitation": "row-level CI may be optimistic due to source/document dependence",
        },
        "cohorts": cohorts,
        "llm_aggrefact_total_including_ragtruth": overall,
        "llm_aggrefact_without_ragtruth_cohort": no_rag_metrics,
        "ragtruth_exclusion": {
            "field": "dataset",
            "excluded_cohort_names": sorted(RAGTRUTH_COHORTS),
            "n_total_before_filter": len(evaluated),
            "n_after_filter": len(without_ragtruth),
        },
        "response_policy_abstentions": {
            "value": None,
            "status": "not_applicable_to_component_path",
            "explanation": (\n                "ResponsePolicy is not run; null means not measured, not zero."
            ),
        },
        "unverified_verdict_count": {
            "value": None,
            "status": "not_applicable_to_component_path",
            "explanation": "Judge 2.0 is not run; UNVERIFIED count is not measured.",
        },
        "record_failures": {
            "n_total": n_total,
            "n_evaluated": len(evaluated),
            "n_failures": n_failures,
            "failure_types": dict(sorted(failures.items())),
            "failure_indices_by_type": failure_indices,
            "failure_rate": n_failures / n_total,
            "policy": (\n                "record-level failures excluded; abort above 1%; no record text in report"
            ),
        },
        "source_file_sha256": sha256_file(dataset),
        "mapping_file_sha256": sha256_file(mapping_path),
        "code_sha": code_sha,
        "code_sha_source": "cli_argument",
        "engine": {
            "class": "RuleStanceDetector",
            "version": RuleStanceDetector.version,
            "weights_or_thresholds_adjusted": False,
        },
        "instance_level_predictions_in_public_artifact": False,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    out_md.write_text(
        "# Detector de stance do ATTRACTOR (componente) — não é o pipeline completo\n\n"
        f"n_total={n_total}; n_avaliado={len(evaluated)}; n_falhas={n_failures}\n\n"
        f"Balanced accuracy (principal): {overall['balanced_accuracy']:.6f}\n\n"
        f"IC95% bootstrap balanced accuracy: [{balanced_ci[0]:.6f}, "
        f"{balanced_ci[1]:.6f}]\n\n"
        f"Accuracy: {overall['accuracy']:.6f}\n\n"
        f"IC95% bootstrap accuracy: [{accuracy_ci[0]:.6f}, "
        f"{accuracy_ci[1]:.6f}]\n\n"
        f"Dataset SHA-256: {report['source_file_sha256']}\n\n"
        f"Mapping SHA-256: {report['mapping_file_sha256']}\n\n"
        f"Code SHA: {code_sha} (source: cli_argument)\n\n"
        "Mede somente RuleStanceDetector, sem Judge 2.0; "
        "não representa acurácia do ATTRACTOR. "
        "Nenhum texto, claim ou previsão por instância incluído.\n",
        encoding="utf-8",
    )
    return report
