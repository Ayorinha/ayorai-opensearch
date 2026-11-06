#!/usr/bin/env python3
"""CPU throughput pilot on a deterministic, stratified 200-row DEV sample.

No predictions, examples, document text, or claims are written to artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import psutil
import torch
from huggingface_hub import HfApi, snapshot_download
from transformers import AutoModelForSequenceClassification, AutoTokenizer

SEED = 20261106
MAX_CHUNK_TOKENS = 384
OVERLAP_TOKENS = 64
BATCH_SIZE = 4
MODELS = [
    {
        "key": "mdeberta_nli",
        "repo": "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
        "prefix": "b5113eb",
    },
    {
        "key": "minicheck_deberta_large",
        "repo": "lytang/MiniCheck-DeBERTa-v3-Large",
        "prefix": "2f2d01a",
    },
]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def resolve_unique_commit(api: HfApi, repo: str, prefix: str) -> str:
    matches = [c.commit_id for c in api.list_repo_commits(repo_id=repo)
               if c.commit_id.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"{repo}: prefix {prefix} resolved to {len(matches)} commits")
    return matches[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_inventory(root: Path, kind: str) -> dict[str, str]:
    if kind == "weights":
        selected = [p for p in root.rglob("*") if p.is_file()
                    and p.name.endswith((".safetensors", ".bin", ".pt"))]
    else:
        keys = ("tokenizer", "vocab", "merges", "sentencepiece", "spiece",
                "special_tokens", "added_tokens", "config.json")
        selected = [p for p in root.rglob("*") if p.is_file()
                    and any(k in p.name.lower() for k in keys)
                    and not p.name.endswith((".safetensors", ".bin", ".pt"))]
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(selected)}


def sentence_chunks(text: str, tokenizer) -> tuple[list[str], int]:
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(str(text)) if s.strip()]
    chunks: list[str] = []
    current: list[int] = []
    all_token_count = 0

    def emit(ids: list[int]) -> None:
        if ids:
            chunks.append(tokenizer.decode(ids, skip_special_tokens=True))

    for sentence in sentences:
        ids = tokenizer.encode(sentence, add_special_tokens=False)
        all_token_count += len(ids)
        if len(ids) > MAX_CHUNK_TOKENS:
            if current:
                emit(current)
                current = current[-OVERLAP_TOKENS:]
            for start in range(0, len(ids), MAX_CHUNK_TOKENS - OVERLAP_TOKENS):
                part = ids[start:start + MAX_CHUNK_TOKENS]
                if part:
                    emit(part)
            current = []
            continue
        if current and len(current) + len(ids) > MAX_CHUNK_TOKENS:
            emit(current)
            current = current[-OVERLAP_TOKENS:]
        current.extend(ids)
    if current:
        emit(current)
    return chunks or [""], all_token_count


def stratified_sample(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    if "dataset" not in frame.columns:
        raise ValueError("Expected LLM-AggreFact coorte column 'dataset'")
    if len(frame) < size:
        raise ValueError(f"DEV has only {len(frame)} rows; need {size}")
    groups = {str(k): g for k, g in frame.groupby("dataset", sort=True)}
    exact = {k: size * len(g) / len(frame) for k, g in groups.items()}
    counts = {k: int(math.floor(v)) for k, v in exact.items()}
    remaining = size - sum(counts.values())
    for k in sorted(groups, key=lambda k: (-(exact[k] - counts[k]), k))[:remaining]:
        counts[k] += 1
    pieces = []
    for i, k in enumerate(sorted(groups)):
        n = counts[k]
        if n:
            pieces.append(groups[k].sample(n=n, random_state=seed + i))
    sample = pd.concat(pieces).sample(frac=1, random_state=seed).reset_index(drop=True)
    if len(sample) != size:
        raise AssertionError("Stratified sampler did not produce exact requested size")
    return sample


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(pd.Series(values).quantile(q))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    df = pd.read_parquet(args.dataset_path)
    required = {"dataset", "doc", "claim"}
    if not required.issubset(df.columns):
        raise ValueError(f"DEV parquet missing expected columns: {sorted(required - set(df.columns))}")
    sample = stratified_sample(df, args.sample_size, args.seed)
    api = HfApi()
    report = {
        "schema_version": "1.0",
        "pilot": "baseline-throughput-dev",
        "split": "dev",
        "dataset_id": "lytang/LLM-AggreFact",
        "dataset_revision": os.environ.get("DEV_REVISION"),
        "dataset_file_sha256": os.environ.get("DEV_SHA256"),
        "code_sha": os.environ.get("GITHUB_SHA"),
        "seed": args.seed,
        "sample_size": len(sample),
        "cohort_field": "dataset",
        "cohort_sample_counts": {str(k): int(v) for k, v in sample["dataset"].value_counts().sort_index().items()},
        "dev_total_rows": int(len(df)),
        "dev_cohort_total_counts": {str(k): int(v) for k, v in df["dataset"].value_counts().sort_index().items()},
        "chunk_policy": {
            "max_tokens": MAX_CHUNK_TOKENS,
            "overlap_tokens": OVERLAP_TOKENS,
            "sentence_aware": True,
            "aggregation": "max score across chunks; quality threshold not evaluated in this pilot",
        },
        "batch_size": BATCH_SIZE,
        "device": "cpu",
        "models": [],
        "instance_level_predictions_in_public_artifact": False,
    }

    process = psutil.Process()
    global_peak_ram = process.memory_info().rss
    for spec in MODELS:
        revision = resolve_unique_commit(api, spec["repo"], spec["prefix"])
        t0 = time.perf_counter()
        model_dir = Path(snapshot_download(repo_id=spec["repo"], revision=revision,
                                          token=None, local_files_only=False))
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            str(model_dir), local_files_only=True, trust_remote_code=False)
        model.eval()
        load_seconds = time.perf_counter() - t0
        peak_ram = process.memory_info().rss

        block_texts: list[str] = []
        claims: list[str] = []
        token_doc_counts: list[int] = []
        token_claim_counts: list[int] = []
        blocks_per_example: list[int] = []
        sample_cohorts: list[str] = []
        for _, row in sample.iterrows():
            chunks, doc_tokens = sentence_chunks(str(row["doc"]), tokenizer)
            claim = str(row["claim"])
            token_doc_counts.append(doc_tokens)
            token_claim_counts.append(len(tokenizer.encode(claim, add_special_tokens=False)))
            blocks_per_example.append(len(chunks))
            sample_cohorts.append(str(row["dataset"]))
            block_texts.extend(chunks)
            claims.extend([claim] * len(chunks))

        inference_start = time.perf_counter()
        processed = 0
        for start in range(0, len(block_texts), BATCH_SIZE):
            docs = block_texts[start:start + BATCH_SIZE]
            clms = claims[start:start + BATCH_SIZE]
            batch = tokenizer(docs, clms, padding=True, truncation=True,
                              max_length=512, return_tensors="pt")
            with torch.inference_mode():
                _ = model(**batch)
            processed += len(docs)
            peak_ram = max(peak_ram, process.memory_info().rss)
        inference_seconds = time.perf_counter() - inference_start
        total_seconds = load_seconds + inference_seconds
        per_example = total_seconds / len(sample)
        cohort_estimates = {}
        for cohort, total_n in report["dev_cohort_total_counts"].items():
            sampled_n = report["cohort_sample_counts"].get(cohort, 0)
            if sampled_n:
                cohort_estimates[cohort] = round(per_example * total_n, 2)

        report["models"].append({
            "model_id": spec["repo"],
            "requested_revision_prefix": spec["prefix"],
            "resolved_revision": revision,
            "weights_sha256": sha256_inventory(model_dir, "weights"),
            "tokenizer_sha256": sha256_inventory(model_dir, "tokenizer"),
            "load_seconds": round(load_seconds, 3),
            "inference_seconds": round(inference_seconds, 3),
            "examples_per_second": round(len(sample) / inference_seconds, 5) if inference_seconds else None,
            "blocks_per_second": round(processed / inference_seconds, 5) if inference_seconds else None,
            "seconds_per_example_including_load": round(per_example, 4),
            "block_count": len(block_texts),
            "mean_blocks_per_example": round(sum(blocks_per_example) / len(blocks_per_example), 3),
            "blocks_per_example_p50": percentile(blocks_per_example, 0.5),
            "blocks_per_example_p95": percentile(blocks_per_example, 0.95),
            "blocks_per_example_max": max(blocks_per_example),
            "document_tokens_mean": round(sum(token_doc_counts) / len(token_doc_counts), 2),
            "document_tokens_p50": percentile(token_doc_counts, 0.5),
            "document_tokens_p95": percentile(token_doc_counts, 0.95),
            "document_tokens_max": max(token_doc_counts),
            "claim_tokens_mean": round(sum(token_claim_counts) / len(token_claim_counts), 2),
            "claim_tokens_p95": percentile(token_claim_counts, 0.95),
            "ram_peak_bytes": int(peak_ram),
            "estimated_full_dev_seconds_by_cohort": cohort_estimates,
            "note": "Forward-pass throughput only; no quality metrics or predictions recorded.",
        })
        global_peak_ram = max(global_peak_ram, peak_ram)
        del model, tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    report["ram_peak_bytes_process"] = int(global_peak_ram)
    report["estimate_note"] = (
        "Extrapolation uses sampled average per-example wall time and full DEV cohort counts; "
        "not a test estimate and not a guarantee. Add safety margin during sharding design."
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"Aggregate pilot report written: {out}; no row-level content emitted.")


if __name__ == "__main__":
    main()
