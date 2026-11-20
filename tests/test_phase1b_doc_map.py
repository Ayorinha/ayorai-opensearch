"""Cache v2: record → document association rebuilt from the pinned DEV file.

Synthetic data only. The end-to-end test runs the aggregator and doc_map.py by file
path, exactly as the workflows do, with several claims per document.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS
from scripts.benchmarks.phase1b.common import sha256_file, stable_record_id
from scripts.benchmarks.phase1b.doc_map import (
    EXPECTED_DEV_FILE,
    build_cache_v2,
    build_doc_map,
    cluster_summary,
    document_id,
    validate_dev_file,
    verify_v2_matches_v1,
)
from scripts.benchmarks.phase1b.score_cache import (
    SCHEMA_VERSION_V2,
    build_score_cache,
    decrypt_score_cache,
    encrypt_score_cache,
)
from tests.test_phase1b_aggregate_cli import _run_aggregator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOC_MAP = REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "doc_map.py"
SCORE_CACHE = REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "score_cache.py"
KEY = bytes(range(32))
CLAIMS_PER_DOC = 4


def _clustered_rows() -> list[dict]:
    rows = []
    for cohort in COHORTS:
        for index in range(40):
            rows.append(
                {
                    "doc": f"SYNTHETIC document {cohort} {index // CLAIMS_PER_DOC}",
                    "claim": f"SYNTHETIC claim {cohort} {index}",
                    "label": index % 2,
                    "dataset": cohort,
                }
            )
    return rows


def _pin_for(path: Path, tmp_path: Path, *, file: str = EXPECTED_DEV_FILE) -> Path:
    pin = {
        "dataset": "lytang/LLM-AggreFact",
        "revision": "a" * 40,
        "file": file,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    pin_path = tmp_path / "pin.json"
    pin_path.write_text(json.dumps(pin), encoding="utf-8")
    return pin_path


def _expected(rows: list[dict]) -> dict[str, tuple[str, str]]:
    return {
        stable_record_id(row): (row["dataset"], "SUPPORTED" if row["label"] else "NOT_SUPPORTED")
        for row in rows
    }


# ---------------------------------------------------------------- unit: the map


def test_doc_id_groups_claims_of_the_same_document_within_a_cohort() -> None:
    rows = _clustered_rows()
    mapping = build_doc_map(rows, _expected(rows))
    assert len(mapping) == len(rows)
    per_doc: dict[str, set[str]] = {}
    for row in rows:
        per_doc.setdefault(mapping[stable_record_id(row)], set()).add(row["doc"])
    assert all(len(docs) == 1 for docs in per_doc.values())
    assert len(per_doc) == len(rows) // CLAIMS_PER_DOC


def test_same_text_in_two_cohorts_is_two_clusters() -> None:
    assert document_id("cohort-a", "same text") != document_id("cohort-b", "same text")
    assert document_id("cohort-a", "same text") == document_id("cohort-a", "same text")


def test_doc_map_is_deterministic() -> None:
    rows = _clustered_rows()
    assert build_doc_map(rows, _expected(rows)) == build_doc_map(
        list(reversed(rows)), _expected(rows)
    )


@pytest.mark.parametrize(
    "case", ["missing", "extra", "label", "cohort", "duplicate", "test_split", "raw_label"]
)
def test_doc_map_fails_closed(case: str) -> None:
    rows = _clustered_rows()
    expected = _expected(rows)
    if case == "missing":
        rows = rows[1:]
        message = "not found"
    elif case == "extra":
        expected.pop(next(iter(expected)))
        message = "not in the cache"
    elif case == "label":
        first = next(iter(expected))
        cohort, gold = expected[first]
        expected[first] = (cohort, "NOT_SUPPORTED" if gold == "SUPPORTED" else "SUPPORTED")
        message = "disagrees"
    elif case == "cohort":
        first = next(iter(expected))
        expected[first] = ("another-cohort", expected[first][1])
        message = "disagrees"
    elif case == "duplicate":
        rows = rows + rows[:1]
        message = "duplicate"
    elif case == "test_split":
        rows = [dict(rows[0], split="test"), *rows[1:]]
        message = "TEST"
    else:
        rows = [dict(rows[0], label=2), *rows[1:]]
        message = "binary mapping"
    with pytest.raises(ValueError, match=message):
        build_doc_map(rows, expected)


def test_dev_file_validation(tmp_path: Path) -> None:
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text("{}\n", encoding="utf-8")
    pin = json.loads(_pin_for(dataset, tmp_path).read_text())
    validate_dev_file(dataset, pin)
    with pytest.raises(ValueError, match="DEV parquet"):
        validate_dev_file(dataset, dict(pin, file="data/test-00000-of-00001.parquet"))
    with pytest.raises(ValueError, match="SHA-256"):
        validate_dev_file(dataset, dict(pin, sha256="0" * 64))
    test_named = tmp_path / "test.jsonl"
    test_named.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="TEST"):
        validate_dev_file(test_named, dict(pin, sha256=sha256_file(test_named)))


# ---------------------------------------------------------------- unit: cache v2


def _v1_cache(rows: list[dict]) -> dict:
    records = [
        {
            "record_id": stable_record_id(row),
            "cohort": row["dataset"],
            "gold": "SUPPORTED" if row["label"] else "NOT_SUPPORTED",
            "score": 0.25 + 0.5 * row["label"],
        }
        for row in rows
    ]
    return build_score_cache(
        {"factcg": records, "minicheck": [dict(r, score=1 - r["score"]) for r in records]},
        protocols={},
        manifest_sha256="m" * 64,
        source_run_id="42",
        calibration_v2={"synthetic": True},
    )


def test_cache_v2_keeps_v1_records_and_round_trips() -> None:
    rows = _clustered_rows()
    v1 = _v1_cache(rows)
    pin = {"revision": "a" * 40, "sha256": "b" * 64}
    v2 = build_cache_v2(v1, build_doc_map(rows, _expected(rows)), pin=pin)
    assert v2["schema_version"] == SCHEMA_VERSION_V2
    assert v2["calibration_v2_sha256"] == v1["calibration_v2_sha256"]
    envelope = encrypt_score_cache(v2, key=KEY, dataset_revision="a" * 40, code_sha="sha")
    assert "SYNTHETIC" not in json.dumps(envelope)
    decrypted = decrypt_score_cache(envelope, key=KEY)
    assert all("doc_id" in r for r in decrypted["models"]["factcg"]["records"])
    # v1 envelopes still decrypt unchanged.
    v1_env = encrypt_score_cache(v1, key=KEY, dataset_revision="a" * 40, code_sha="sha")
    assert "doc_id" not in decrypt_score_cache(v1_env, key=KEY)["models"]["factcg"]["records"][0]


def test_cache_v2_detects_tampering_and_bad_doc_ids() -> None:
    rows = _clustered_rows()
    v1 = _v1_cache(rows)
    pin = {"revision": "a" * 40, "sha256": "b" * 64}
    v2 = build_cache_v2(v1, build_doc_map(rows, _expected(rows)), pin=pin)
    tampered = json.loads(json.dumps(v2))
    tampered["models"]["factcg"]["records"][0]["score"] = 0.123
    with pytest.raises(ValueError, match="differ from v1"):
        verify_v2_matches_v1(v1, tampered)
    bad = json.loads(json.dumps(v2))
    bad["models"]["factcg"]["records"][0]["doc_id"] = "not-a-digest"
    envelope = encrypt_score_cache(bad, key=KEY, dataset_revision="a" * 40, code_sha="sha")
    with pytest.raises(ValueError, match="doc_id"):
        decrypt_score_cache(envelope, key=KEY)


def test_cluster_summary_is_aggregate_only() -> None:
    rows = _clustered_rows()
    v2 = build_cache_v2(
        _v1_cache(rows),
        build_doc_map(rows, _expected(rows)),
        pin={"revision": "a" * 40, "sha256": "b" * 64},
    )
    summary = cluster_summary(v2, replay_status="skipped")
    assert summary["documents_total"] == len(rows) // CLAIMS_PER_DOC
    for cohort in COHORTS:
        item = summary["cohorts"][cohort]
        assert item["claims"] == 40 and item["documents"] == 40 // CLAIMS_PER_DOC
        assert item["claims_per_document"]["max"] == CLAIMS_PER_DOC
    serialized = json.dumps(summary)
    assert 'doc_id"' not in serialized and "record_id" not in serialized
    assert not any(stable_record_id(row) in serialized for row in rows)


# ---------------------------------------------------------------- end to end


def test_cli_builds_v2_with_identical_calibration_replay(tmp_path: Path) -> None:
    rows = _clustered_rows()
    cache_v1 = tmp_path / "cache" / "phase1b-dev-score-cache.json"
    completed, _, context = _run_aggregator(
        tmp_path, "--score-cache-output", str(cache_v1), "--code-sha", "synthetic", rows=rows
    )
    assert completed.returncode == 0, completed.stderr

    dataset = tmp_path / "dev.jsonl"
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    pin = _pin_for(dataset, tmp_path)
    cache_v2 = tmp_path / "v2" / "phase1b-dev-score-cache.json"
    summary_path = tmp_path / "out" / "summary.json"
    built = subprocess.run(
        [
            sys.executable,
            str(DOC_MAP),
            "--cache",
            str(cache_v1),
            "--dataset-path",
            str(dataset),
            "--pin",
            str(pin),
            "--output-cache",
            str(cache_v2),
            "--summary-output",
            str(summary_path),
        ],
        cwd=tmp_path,
        env=context["env"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr
    summary = json.loads(summary_path.read_text())
    assert summary["calibration_v2_replay"] == "matches_source"
    assert summary["documents_total"] == len(rows) // CLAIMS_PER_DOC
    assert not any(record_id in summary_path.read_text() for record_id in context["rows_by_id"])
    assert "SYNTHETIC" not in cache_v2.read_text()

    # Registered experiments run unchanged on the v2 cache.
    replay_out = tmp_path / "replay.json"
    replay = subprocess.run(
        [
            sys.executable,
            str(SCORE_CACHE),
            "--cache",
            str(cache_v2),
            "--experiment",
            "replay-calibration-v2",
            "--output",
            str(replay_out),
        ],
        cwd=tmp_path,
        env=context["env"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay_out.read_text())["replay_matches_source"] is True


def test_doc_id_collision_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.benchmarks.phase1b import doc_map

    rows = _clustered_rows()
    monkeypatch.setattr(doc_map, "document_id", lambda cohort, doc: "f" * 64)
    with pytest.raises(ValueError, match="collision"):
        doc_map.build_doc_map(rows, _expected(rows))
