from __future__ import annotations

"""Local-only evaluation adapter for LLM-AggreFact; it never downloads data."""
import csv, hashlib, json
from pathlib import Path
from typing import Any
from ayorai_attractor.evaluation.golden import _git_sha
from ayorai_attractor.evaluation.stats import bootstrap_accuracy
from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim, RetrievedDocument
from ayorai_attractor.verification.models import Claim, Stance
from ayorai_attractor.verification.response import ResponsePolicy
from ayorai_attractor.verification.stance import RuleStanceDetector

SCHEMA_VERSION = "1.0.0"
SEED = 20261003
ITERATIONS = 10000

class DatasetError(ValueError):
    pass

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        result = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip(): continue
            try: item = json.loads(line)
            except json.JSONDecodeError as exc: raise DatasetError(f"invalid JSON at line {n}") from exc
            if not isinstance(item, dict): raise DatasetError(f"line {n} is not an object")
            result.append(item)
        return result
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as f: return list(csv.DictReader(f))
    if path.suffix.lower() in {".parquet", ".pq"}:
        try: import pyarrow.parquet as pq
        except ImportError as exc: raise DatasetError("Parquet requires pyarrow") from exc
        return pq.read_table(path).to_pylist()
    raise DatasetError("Use JSONL, CSV, or Parquet")

def load_mapping(path: Path) -> dict[str, Any]:
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise DatasetError("invalid mapping file") from exc
    if data.get("schema_version") != "1.0.0" or data.get("mapping_id") != "llm-aggrefact-label-map-v1":
        raise DatasetError("unsupported label mapping version")
    return data

def adapt_records(records: list[dict[str, Any]], mapping: dict[str, Any]) -> list[dict[str, str]]:
    adapted = []
    for i, row in enumerate(records):
        missing = [k for k in ("doc", "claim", "label", "dataset") if k not in row]
        if missing: raise DatasetError(f"record {i} missing fields: {missing}")
        if not isinstance(row["doc"], str) or not row["doc"].strip() or not isinstance(row["claim"], str) or not row["claim"].strip():
            raise DatasetError(f"record {i}: doc/claim must be nonempty strings")
        label = mapping["native_binary_labels"].get(str(row["label"]))
        if label not in {"SUPPORTED", "NOT_SUPPORTED"}: raise DatasetError(f"record {i}: unknown label; no silent drop")
        if not isinstance(row["dataset"], str) or not row["dataset"].strip(): raise DatasetError(f"record {i}: missing dataset cohort")
        adapted.append({"doc": row["doc"], "claim": row["claim"], "label": label, "dataset": row["dataset"].strip(), "record_id": str(i)})
    if not adapted: raise DatasetError("empty dataset")
    return adapted

def predict(row: dict[str, str], detector: RuleStanceDetector) -> tuple[str, str]:
    claim = Claim(id="claim-1", text=row["claim"])
    digest = hashlib.sha256(row["claim"].encode()).hexdigest()
    extracted = ExtractedClaim(claim, 1.0, ComponentProvenance("benchmark-adapter", "local", "1", digest, digest))
    from datetime import datetime, timezone
    doc = RetrievedDocument(id="evidence-1", content=row["doc"], source_id="local-file", source_location="local-record:" + row["record_id"], retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc), origin_id="local-file", end_offset=len(row["doc"]))
    detected = detector.detect([extracted], [doc.to_evidence("claim-1")])
    if len(detected.edges) != 1: raise DatasetError(f"record {row['record_id']}: detector output cardinality mismatch")
    stance = detected.edges[0].edge.stance
    return ("SUPPORTED" if stance is Stance.SUPPORTS else "NOT_SUPPORTED", stance.value.upper())

def metrics(gold: list[str], pred: list[str]) -> dict[str, Any]:
    labels = ("SUPPORTED", "NOT_SUPPORTED")
    cm = {a: {b: 0 for b in labels} for a in labels}
    for a, b in zip(gold, pred, strict=True): cm[a][b] += 1
    per_class = {}
    recalls = []
    for label in labels:
        tp = cm[label][label]; fn = sum(cm[label][x] for x in labels if x != label); fp = sum(cm[x][label] for x in labels if x != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"support": tp + fn, "precision": precision, "recall": recall, "f1": f1}
        if tp + fn: recalls.append(recall)
    from collections import Counter
    counts = Counter(gold); majority, nmajor = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
    return {"n": len(gold), "balanced_accuracy": sum(recalls) / len(recalls), "accuracy": sum(a == b for a,b in zip(gold,pred,strict=True))/len(gold), "per_class": per_class, "confusion_matrix": cm, "majority_baseline": {"label": majority, "accuracy": nmajor/len(gold)}}

def evaluate(dataset: Path, mapping_path: Path, out_json: Path, out_md: Path) -> dict[str, Any]:
    mapping = load_mapping(mapping_path)
    rows = adapt_records(read_records(dataset), mapping)
    detector = RuleStanceDetector()
    predictions = []
    for row in rows:
        pred, stance = predict(row, detector)
        predictions.append((row, pred, stance))
    gold = [row["label"] for row, _, _ in predictions]; pred = [p for _, p, _ in predictions]
    overall = metrics(gold, pred)
    lo, hi = bootstrap_accuracy(gold, pred, iterations=ITERATIONS, seed=SEED)
    cohorts = {cohort: metrics([r["label"] for r,_,_ in predictions if r["dataset"] == cohort], [p for r,p,_ in predictions if r["dataset"] == cohort]) for cohort in sorted({r["dataset"] for r,_,_ in predictions})}
    rag_names = {"ragtruth", "rag-truth"}
    no_rag = [(r,p,s) for r,p,s in predictions if r["dataset"].casefold() not in rag_names]
    if not no_rag: raise DatasetError("RAGTruth-excluded cohort empty; refusing report")
    report = {"schema_version": SCHEMA_VERSION, "dataset": "LLM-AggreFact", "mapping_id": mapping["mapping_id"], "task": "binary_claim_document_support", "primary_metric": "balanced_accuracy", "metrics": overall, "bootstrap_ci95_accuracy": {"lower":lo,"upper":hi,"iterations":ITERATIONS,"seed":SEED,"unit":"individual claim-document rows sampled with replacement","clustered":False,"limitation":"record-level interval may be optimistic under source dependence"}, "cohorts":cohorts, "llm_aggrefact_total_including_ragtruth":overall, "llm_aggrefact_without_ragtruth_cohort":metrics([r["label"] for r,_,_ in no_rag],[p for _,p,_ in no_rag]), "response_policy_abstentions": {item.value: 0 for item in ResponsePolicy}, "response_policy_note": "Direct local RuleStanceDetector path does not emit transport abstentions; these are separate from neutral stance.", "unverified_verdict_count": 0, "unverified_verdict_note": "This harness evaluates stance-derived binary outputs; UNVERIFIED is not generated as a transport abstention or silently merged into the abstention count.", "neutral_stance_count":sum(s == "NEUTRAL" for _,_,s in predictions), "failure_policy":"fail-fast; no silent exclusions", "source_file_sha256":sha256_file(dataset), "mapping_file_sha256":sha256_file(mapping_path), "code_sha":_git_sha(), "engine":{"class":"RuleStanceDetector","version":RuleStanceDetector.version,"weights_or_thresholds_adjusted":False}, "instance_level_predictions_in_public_artifact":False}
    out_json.parent.mkdir(parents=True, exist_ok=True); out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    out_md.write_text("# Aggregate LLM-AggreFact report\n\n" + f"n={overall['n']}\n\nBalanced accuracy: {overall['balanced_accuracy']:.6f}\n\nAccuracy: {overall['accuracy']:.6f}\n\n95% bootstrap CI: [{lo:.6f}, {hi:.6f}]\n\nInput SHA-256: `{report['source_file_sha256']}`\n\nMapping SHA-256: `{report['mapping_file_sha256']}`\n\nCode SHA: `{report['code_sha']}`\n\nNo per-record texts, labels or predictions included.\n", encoding="utf-8")
    return report
