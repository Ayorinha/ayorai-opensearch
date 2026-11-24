#!/usr/bin/env python3
"""Run one pinned FP32 model on one DEV shard; write private local output only."""

from __future__ import annotations

import argparse
import json
import os
import re
import resource
import time
from pathlib import Path
from typing import Any

try:
    from .common import (
        MANIFEST_SCHEMA_VERSION,
        MODELS,
        RECORD_ID_METHOD,
        atomic_write_bytes,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
    from .nltk_resources import load_pin as load_nltk_pin
    from .nltk_resources import prepare_runtime as prepare_nltk_runtime
    from .protocols import (
        assert_all_fp32,
        chunk_factcg,
        chunk_minicheck,
        format_single_texts,
        get_protocol,
    )
except ImportError:  # direct script execution
    from common import (
        MANIFEST_SCHEMA_VERSION,
        MODELS,
        RECORD_ID_METHOD,
        atomic_write_bytes,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
    from nltk_resources import load_pin as load_nltk_pin
    from nltk_resources import prepare_runtime as prepare_nltk_runtime
    from protocols import (
        assert_all_fp32,
        chunk_factcg,
        chunk_minicheck,
        format_single_texts,
        get_protocol,
    )


def select_shard(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    shard_id: str,
) -> list[tuple[str, dict[str, Any]]]:
    if (
        manifest.get("split") != "dev"
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("record_id_method") != RECORD_ID_METHOD
    ):
        raise ValueError("runner accepts only current inference-only DEV manifests")
    indexed: dict[str, dict[str, Any]] = {}
    allowed_fields = {"record_id", "doc", "claim", "dataset"}
    for row in rows:
        if set(row) != allowed_fields:
            raise ValueError("inference input must contain only record_id, doc, claim and dataset")
        record_id = row["record_id"]
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("inference record_id must be a non-empty string")
        if record_id in indexed:
            raise ValueError("duplicate inference record_id")
        indexed[record_id] = row
    shard = next((item for item in manifest["shards"] if item["shard_id"] == shard_id), None)
    if shard is None:
        raise ValueError("requested shard is absent from manifest")
    if len(shard["record_ids"]) != shard["count"]:
        raise ValueError("manifest shard count is inconsistent")
    selected = []
    for rid in shard["record_ids"]:
        if rid not in indexed:
            raise ValueError("manifest row digest is absent from pinned DEV data")
        row = indexed[rid]
        if stable_record_id(row) != rid:
            raise ValueError("inference record_id does not match its content")
        selected.append((rid, row))
    return selected


def _sentence_chunks(
    text: str,
    tokenizer: Any,
    max_tokens: int = 384,
