#!/usr/bin/env python3
"""Run one pinned FP32 model on one DEV shard; write private local output only."""

from __future__ import annotations

import argparse
import json
import re
import resource
import time
from pathlib import Path
from typing import Any

try:
    from .common import DEV_PIN_PATH, MODELS, load_records, sha256_file, stable_record_id
except ImportError:  # direct script execution
    from common import DEV_PIN_PATH, MODELS, load_records, sha256_file, stable_record_id


def select_shard(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    shard_id: str,
) -> list[tuple[str, dict[str, Any]]]:
    if manifest.get("split") != "dev":
        raise ValueError("TEST execution is forbidden in the Phase 1b DEV runner")
    indexed = {stable_record_id(row): row for row in rows}
    shard = next((item for item in manifest["shards"] if item["shard_id"] == shard_id), None)
    if shard is None:
        raise ValueError("requested shard is absent from manifest")
    if len(shard["record_ids"]) != shard["count"]:
        raise ValueError("manifest shard count is inconsistent")
    selected = []
    for rid in shard["record_ids"]:
        if rid not in indexed:
            raise ValueError("manifest row digest is absent from pinned DEV data")
        selected.append((rid, indexed[rid]))
    return selected


def _sentence_chunks(
    text: str,
    tokenizer: Any,
    max_tokens: int = 384,
    overlap: int = 64,
) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]
    chunks: list[str] = []
    current: list[int] = []
    for sentence in sentences:
        token_ids = tokenizer.encode(sentence, add_special_tokens=False)
        if len(token_ids) > max_tokens:
            if current:
                chunks.append(tokenizer.decode(current, skip_special_tokens=True))
                current = current[-overlap:]
            for start in range(0, len(token_ids), max_tokens - overlap):
                chunk = token_ids[start : start + max_tokens]
                chunks.append(tokenizer.decode(chunk, skip_special_tokens=True))
            current = []
            continue
        if current and len(current) + len(token_ids) > max_tokens:
            chunks.append(tokenizer.decode(current, skip_special_tokens=True))
            current = current[-overlap:]
        current.extend(token_ids)
    if current:
        chunks.append(tokenizer.decode(current, skip_special_tokens=True))
    return chunks or [""]


def _support_label_id(config: Any) -> int:
    labels = {int(index): str(label).casefold() for index, label in config.id2label.items()}
    support_terms = ("entail", "support", "positive")
    matches = [
        index for index, label in labels.items() if any(term in label for term in support_terms)
    ]
    if len(matches) != 1:
        raise ValueError(
            "model config does not expose one unambiguous support label; explicit mapping required"
        )
    return matches[0]


def run_inference(
    selected: list[tuple[str, dict[str, Any]]],
    *,
    model_id: str,
    sort_by_length: bool = True,
    batch_size: int = 4,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if model_id not in MODELS:
        raise ValueError("unknown model id")
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    spec = MODELS[model_id]
    model_dir = Path(snapshot_download(repo_id=spec["repo"], revision=spec["revision"]))
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), local_files_only=True, trust_remote_code=False
    )
    model.eval()
    if any(parameter.dtype != torch.float32 for parameter in model.parameters()):
        raise RuntimeError("model weights are not FP32")
    support_id = _support_label_id(model.config)

    started = time.perf_counter()
    expanded: list[tuple[str, str, str, str]] = []
    for rid, row in selected:
        claim = str(row["claim"])
        for chunk_index, chunk in enumerate(_sentence_chunks(str(row["doc"]), tokenizer)):
            expanded.append((rid, claim, chunk, f"{rid}:{chunk_index:06d}"))
    if sort_by_length:
        expanded.sort(
            key=lambda item: (
                len(tokenizer.encode(item[2], add_special_tokens=False)),
                item[0],
                item[3],
            )
        )
    else:
        expanded.sort(key=lambda item: (item[0], item[3]))

    token_total = sum(len(tokenizer.encode(item[2], add_special_tokens=False)) for item in expanded)
    tokenization_seconds = time.perf_counter() - started
    truncation_count = 0
    inference_started = time.perf_counter()
    scores: dict[str, float] = {}
    with torch.inference_mode():
        for offset in range(0, len(expanded), batch_size):
            batch_rows = expanded[offset : offset + batch_size]
            docs = [item[2] for item in batch_rows]
            claims = [item[1] for item in batch_rows]
            inputs = tokenizer(
                docs,
                claims,
                padding=True,
                truncation="only_first",
                max_length=512,
                return_tensors="pt",
                return_overflowing_tokens=False,
            )
            truncation_count += sum(
                1
                for doc, claim in zip(docs, claims, strict=True)
                if len(tokenizer(doc, claim, add_special_tokens=True)["input_ids"]) > 512
            )
            logits = model(**inputs).logits
            probabilities = torch.softmax(logits.float(), dim=-1)[:, support_id].tolist()
            for item, score in zip(batch_rows, probabilities, strict=True):
                scores[item[0]] = max(scores.get(item[0], 0.0), float(score))

    inference_seconds = time.perf_counter() - inference_started
    records = [
        {
            "record_id": rid,
            "gold": "SUPPORTED" if str(row["label"]) == "1" else "NOT_SUPPORTED",
            "score": scores[rid],
        }
        for rid, row in sorted(selected, key=lambda pair: pair[0])
    ]
    operational = {
        "document_count": len(selected),
        "block_count": len(expanded),
        "token_count_by_unit": {f"{model_id}_tokenizer_tokens": token_total},
        "tokenization_seconds": tokenization_seconds,
        "inference_seconds": inference_seconds,
        "total_seconds": time.perf_counter() - started,
        # ru_maxrss is reported in KiB on Linux runners.
        "peak_ram_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "truncation_count": truncation_count,
        "failure_count": 0,
    }
    return records, operational


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--shard-id", required=True)
    parser.add_argument("--model-id", choices=sorted(MODELS), required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--order-by-length", action="store_true")
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pin = json.loads(DEV_PIN_PATH.read_text(encoding="utf-8"))
    if (
        sha256_file(args.dataset_path) != pin["sha256"]
        or manifest["dataset_sha256"] != pin["sha256"]
    ):
        raise ValueError("DEV dataset does not match the immutable pin")
    selected = select_shard(manifest, load_records(args.dataset_path), args.shard_id)
    result, operational = run_inference(
        selected,
        model_id=args.model_id,
        sort_by_length=args.order_by_length,
        batch_size=args.batch_size,
    )
    package = {
        "schema_version": "phase1b-private-shard-v1",
        "split": "dev",
        "shard_id": args.shard_id,
        "model_id": args.model_id,
        "model_revision": MODELS[args.model_id]["revision"],
        "dataset_revision": manifest["dataset_revision"],
        "dataset_sha256": manifest["dataset_sha256"],
        "code_sha": manifest["code_sha"],
        **operational,
        "records": result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(package, sort_keys=True, separators=(",", ":"))
    args.output.write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "shard_complete",
                "split": "dev",
                "shard_id": args.shard_id,
                "model_id": args.model_id,
                "record_count": len(result),
            }
        )
    )


if __name__ == "__main__":
    main()
