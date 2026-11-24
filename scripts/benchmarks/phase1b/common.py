"""Shared deterministic and privacy-preserving helpers for Phase 1b."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

DEV_PIN_PATH = Path("configs/benchmarks/llm-aggrefact-dev-pin.json")
MANIFEST_SCHEMA_VERSION = "phase1b-dev-manifest-v2"
RECORD_ID_METHOD = 'sha256(canonical_json({"doc": ..., "claim": ..., "dataset": ...}))'
LABEL_MAP_PATH = Path("configs/benchmarks/llm-aggrefact-label-map-v1.json")
MODELS: dict[str, dict[str, str]] = {
    "mdeberta": {
        "repo": "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
        "revision": "b5113eb38ab63efdd7f280f8c144ea8b13f978ce",
        "weights": "safetensors",
    },
    "minicheck": {
        "repo": "lytang/MiniCheck-DeBERTa-v3-Large",
        "revision": "2f2d01a54fa022a7ffadb76260e1ea8bc88c82bb",
        "weights": "bin",
    },
    "factcg": {
        "repo": "yaxili96/FactCG-DeBERTa-v3-Large",
        "revision": "0430e3509dbd28d2dff7a117c0eae25359ff3e80",
        "weights": "safetensors",
    },
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    """Read JSONL or Parquet; never echo row content in exceptions."""
    if not path.is_file():
        raise ValueError("dataset file is unavailable")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("dataset row must be an object")
                rows.append(item)
        return rows
    if path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("Parquet support requires pyarrow") from exc
        return pq.read_table(path).to_pylist()
    raise ValueError("supported dataset formats are JSONL and Parquet")


def stable_record_id(row: dict[str, Any]) -> str:
    """Hash inference inputs only; the gold label never influences the record ID."""
    identity = {
        "doc": row["doc"],
        "claim": row["claim"],
        "dataset": row["dataset"],
    }
    return sha256_bytes(canonical_json(identity))


def safe_failure(exc: BaseException) -> dict[str, str]:
    """Return only a non-sensitive exception class; never stringify exceptions."""
    return {"error_type": type(exc).__name__}


def atomic_write_bytes(path: Path, payload: bytes, *, mode: int = 0o600) -> None:
    """Atomically replace a file with restrictive permissions and durable contents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise
