"""Adversarial tests for the P3/A1 DEV isolation, derived from the threat model.

Each test names the threat it refutes. Synthetic data only: no DEV/TEST record, no
secret, no network. The pinned DEV revision and digest are public metadata.
"""

from __future__ import annotations

import base64
import json
import secrets
from pathlib import Path
from typing import Any

import pytest
from cryptography.exceptions import InvalidTag

from scripts.benchmarks.phase1b import common, emit_matrix, manifest_artifact, score_cache
from scripts.benchmarks.phase1b import inference_artifact as inference
from scripts.benchmarks.phase1b import prepare_dev_artifacts as prepare
from scripts.benchmarks.phase1b.encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes

PIN = json.loads(common.DEV_PIN_PATH.read_text(encoding="utf-8"))
CODE_SHA = "c" * 40
META = {
    "run_id": "101",
    "split": "dev",
    "model_revision": "shared-inference-v1",
    "shard_id": "all",
    "dataset_revision": PIN["revision"],
    "code_sha": CODE_SHA,
}


def _rows(n: int = 6) -> list[dict[str, str]]:
    return [
        {
            "doc": f"doc {i}",
            "claim": f"claim {i}",
            "dataset": "A" if i % 2 else "B",
            "label": str(i % 2),
        }
        for i in range(n)
    ]


def _seal(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = common.sha256_bytes(common.canonical_json(manifest))
    return manifest


def _manifest(rows: list[dict[str, str]] | None = None) -> dict[str, Any]:
    ids = sorted(common.stable_record_id(row) for row in rows or _rows())
    shard = {
        "shard_id": "dev-0000",
        "count": len(ids),
        "record_ids": ids,
        "record_ids_sha256": common.sha256_bytes(common.canonical_json(ids)),
    }
    return _seal(
        {
            "split": "dev",
            "schema_version": common.MANIFEST_SCHEMA_VERSION,
            "record_id_method": common.RECORD_ID_METHOD,
            "dataset_revision": PIN["revision"],
            "dataset_sha256": PIN["sha256"],
            "code_sha": CODE_SHA,
            "sample_count": len(ids),
            "shards": [shard],
        }
    )


def _flip(envelope: dict[str, Any], field: str, index: int) -> dict[str, Any]:
    raw = bytearray(base64.b64decode(envelope[field]))
    raw[index] ^= 1
    return {**envelope, field: base64.b64encode(bytes(raw)).decode()}


@pytest.fixture
def prepared(tmp_path: Path) -> dict[str, Any]:
    gold_key = secrets.token_bytes(32)
    manifest = prepare.prepare(
        _rows(),
        _manifest(),
        source_run_id="101",
        code_sha=CODE_SHA,
        gold_key=gold_key,
        inference_output=tmp_path / "inference.jsonl",
        gold_label_output=tmp_path / "gold.json",
    )
    return {"manifest": manifest, "gold_key": gold_key, "dir": tmp_path}


# --- threat: the gold label leaks into inference or its identity ------------------------


def test_record_identity_does_not_depend_on_the_gold_label() -> None:
    row = {"doc": "d", "claim": "c", "dataset": "X", "label": "1"}
    assert common.stable_record_id(row) == common.stable_record_id({**row, "label": "0"})
    assert common.stable_record_id(row) != common.stable_record_id({**row, "claim": "c2"})


def test_inference_input_has_exactly_the_four_inference_fields(prepared: dict[str, Any]) -> None:
    lines = (prepared["dir"] / "inference.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    assert all(set(json.loads(line)) == {"record_id", "doc", "claim", "dataset"} for line in lines)
    assert (prepared["dir"] / "inference.jsonl").stat().st_mode & 0o777 == 0o600


def test_gold_label_cache_is_ciphertext_and_needs_its_own_key(prepared: dict[str, Any]) -> None:
    text = (prepared["dir"] / "gold.json").read_text(encoding="utf-8")
    assert "SUPPORTED" not in text
    envelope = json.loads(text)
    with pytest.raises(InvalidTag):
        score_cache.decrypt_gold_label_cache(envelope, key=secrets.token_bytes(32))
    labels = score_cache.decrypt_gold_label_cache(envelope, key=prepared["gold_key"])
    assert {row["gold"] for row in labels["records"]} == {"SUPPORTED", "NOT_SUPPORTED"}


@pytest.mark.parametrize("field", ["gold", "label", "gold_label", "is_supported"])
def test_score_record_with_any_label_like_field_is_refused(field: str) -> None:
    record = {"record_id": "a" * 64, "cohort": "A", "score": 0.5, field: "SUPPORTED"}
    with pytest.raises(ValueError):
        score_cache._clean_score_record(record)


@pytest.mark.parametrize(
    "record",
    [
        {"record_id": "a", "cohort": "A", "gold": "MAYBE"},
        {"record_id": "a", "cohort": "A", "gold": "SUPPORTED", "score": 0.9},
        {"record_id": "a", "cohort": "A"},
    ],
)
def test_gold_label_record_must_be_exact(record: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        score_cache._clean_label_record(record)


def test_conflicting_duplicates_are_excluded_instead_of_choosing_a_label(tmp_path: Path) -> None:
    """DEC-034 A: an identity whose copies disagree on the label never reaches inference."""
    rows = _rows()
    conflicted = [*rows, {**rows[0], "label": "0" if rows[0]["label"] == "1" else "1"}]
    # A manifest that still selects the conflicting identity cannot be prepared.
    with pytest.raises(ValueError, match="absent from pinned DEV source"):
        prepare.prepare(
            conflicted,
            _manifest(rows),
            source_run_id="101",
            code_sha=CODE_SHA,
            gold_key=secrets.token_bytes(32),
            inference_output=tmp_path / "i",
            gold_label_output=tmp_path / "g",
        )
    # Without it, the remaining rows prepare normally and the excluded one is absent.
    prepare.prepare(
        conflicted,
        _manifest(rows[1:]),
        source_run_id="101",
        code_sha=CODE_SHA,
        gold_key=None,
        inference_output=tmp_path / "i",
        gold_label_output=None,
    )
    written = (tmp_path / "i").read_text(encoding="utf-8")
    assert common.stable_record_id(rows[0]) not in written
    assert written.count("record_id") == len(rows) - 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda m: m.update(split="test"), "only current inference-only DEV manifests"),
        (lambda m: m.update(record_id_method="v1"), "only current inference-only DEV manifests"),
        (lambda m: m.update(code_sha="d" * 40), "source DEV manifest digest"),
    ],
)
def test_prepare_refuses_foreign_or_edited_manifests(
    tmp_path: Path, mutate: Any, message: str
) -> None:
    manifest = _manifest()
    mutate(manifest)
    with pytest.raises(ValueError, match=message):
        prepare.prepare(
            _rows(),
            manifest,
            source_run_id="101",
            code_sha=CODE_SHA,
            gold_key=secrets.token_bytes(32),
            inference_output=tmp_path / "i",
            gold_label_output=tmp_path / "g",
        )


def test_prepare_refuses_labels_outside_the_binary_mapping(tmp_path: Path) -> None:
    rows = _rows()
    rows[0] = {**rows[0], "label": "2"}
    with pytest.raises(ValueError, match="frozen binary mapping"):
        prepare.prepare(
            rows,
            _manifest(rows),
            source_run_id="101",
            code_sha=CODE_SHA,
            gold_key=secrets.token_bytes(32),
            inference_output=tmp_path / "i",
            gold_label_output=tmp_path / "g",
        )


def test_prepare_refuses_records_absent_from_the_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absent from pinned DEV source"):
        prepare.prepare(
            _rows()[:-1],
            _manifest(),
            source_run_id="101",
            code_sha=CODE_SHA,
            gold_key=secrets.token_bytes(32),
            inference_output=tmp_path / "i",
            gold_label_output=tmp_path / "g",
        )


# --- threat: ciphertext or envelope tampering, cross-artifact replay --------------------


@pytest.mark.parametrize(
    ("field", "index"), [("ciphertext_b64", 0), ("ciphertext_b64", -1), ("nonce_b64", 0)]
)
def test_any_bit_flip_in_ciphertext_tag_or_nonce_is_refused(field: str, index: int) -> None:
    key = secrets.token_bytes(32)
    envelope = encrypt_bytes(b"payload", key=key, metadata=META)
    with pytest.raises(InvalidTag):
        decrypt_bytes(_flip(envelope, field, index), key=key, aad_metadata=META)


@pytest.mark.parametrize(
    "other",
    [
        {"model_revision": "shared-dev-manifest-v1"},
        {"run_id": "102"},
        {"code_sha": "d" * 40},
        {"dataset_revision": "other"},
        {"shard_id": "dev-0001"},
    ],
)
def test_envelope_from_another_role_run_or_revision_is_refused(other: dict[str, str]) -> None:
    key = secrets.token_bytes(32)
    envelope = encrypt_bytes(b"payload", key=key, metadata={**META, **other})
    with pytest.raises(InvalidTag):
        decrypt_bytes(envelope, key=key, aad_metadata=META)


def test_nonces_do_not_repeat() -> None:
    key = secrets.token_bytes(32)
    nonces = {encrypt_bytes(b"x", key=key, metadata=META)["nonce_b64"] for _ in range(2000)}
    assert len(nonces) == 2000


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({**META, "split": "test"}, "only DEV"),
        ({**META, "code_sha": ""}, "incomplete"),
        ({key: value for key, value in META.items() if key != "run_id"}, "incomplete"),
    ],
)
def test_encryption_refuses_non_dev_or_incomplete_context(
    metadata: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        encrypt_bytes(b"x", key=secrets.token_bytes(32), metadata=metadata)


@pytest.mark.parametrize(
    "raw",
    [None, "", "not base64!", base64.b64encode(bytes(16)).decode()],
)
def test_keys_must_be_present_base64_and_256_bit(raw: str | None, monkeypatch: Any) -> None:
    monkeypatch.delenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", raising=False)
    with pytest.raises((RuntimeError, ValueError)):
        decode_key(raw)


def test_gold_envelope_cannot_pose_as_a_score_cache(prepared: dict[str, Any]) -> None:
    envelope = json.loads((prepared["dir"] / "gold.json").read_text(encoding="utf-8"))
    key = prepared["gold_key"]
    with pytest.raises(ValueError):
        score_cache.decrypt_score_cache(envelope, key=key)
    disguised = {
        **envelope,
        "metadata": {
            **envelope["metadata"],
            "model_revision": "multi-model-score-cache",
            "shard_id": score_cache.SCORE_CACHE_SHARD_ID,
        },
    }
    with pytest.raises(InvalidTag):
        score_cache.decrypt_score_cache(disguised, key=key)


# --- threat: inference input altered between jobs (#636) --------------------------------


def test_inference_input_is_bound_to_the_manifest_digest(prepared: dict[str, Any]) -> None:
    directory, manifest = prepared["dir"], prepared["manifest"]
    key = secrets.token_bytes(32)
    metadata = inference.inference_metadata(manifest, run_id="101", code_sha=CODE_SHA)
    tampered = directory / "tampered.jsonl"
    tampered.write_bytes((directory / "inference.jsonl").read_bytes() + b"{}\n")
    with pytest.raises(ValueError, match="does not match"):
        inference.encrypt_inference_file(
            tampered,
            directory / "enc",
            key=key,
            metadata=metadata,
            expected_sha256=manifest["inference_dataset_sha256"],
        )
    assert not (directory / "enc").exists()
    inference.encrypt_inference_file(
        directory / "inference.jsonl",
        directory / "enc",
        key=key,
        metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )
    with pytest.raises(ValueError, match="does not match"):
        inference.decrypt_inference_file(
            directory / "enc",
            directory / "out",
            key=key,
            expected_metadata=metadata,
            expected_sha256="0" * 64,
        )
    assert not (directory / "out").exists()
    assert not [path.name for path in directory.iterdir() if path.name.startswith(".")]


# --- threat: joining caches from different runs, manifests or coverage ------------------


def _score_cache_for(labels: dict[str, Any], run: str) -> dict[str, Any]:
    records = [
        {"record_id": row["record_id"], "cohort": row["cohort"], "score": 0.5}
        for row in labels["records"]
    ]
    return {
        "split": "dev",
        "source_run_id": run,
        "manifest_sha256": labels["manifest_sha256"],
        "record_count": labels["record_count"],
        "models": {"m": {"protocol": "p", "records": records}},
    }


def test_join_refuses_caches_from_different_runs_or_coverage(prepared: dict[str, Any]) -> None:
    envelope = json.loads((prepared["dir"] / "gold.json").read_text(encoding="utf-8"))
    labels = score_cache.decrypt_gold_label_cache(envelope, key=prepared["gold_key"])
    joined = score_cache.join_scores_with_gold(_score_cache_for(labels, "101"), labels)
    assert joined["record_fields"] == ["record_id", "cohort", "gold", "score"]
    with pytest.raises(ValueError, match="source_run_id"):
        score_cache.join_scores_with_gold(_score_cache_for(labels, "102"), labels)
    short = {**labels, "records": labels["records"][:-1]}
    with pytest.raises(ValueError):
        score_cache.join_scores_with_gold(_score_cache_for(labels, "101"), short)
    swapped = json.loads(json.dumps(labels))
    swapped["records"][0]["cohort"] = "Z"
    with pytest.raises(ValueError, match="cohort"):
        score_cache.join_scores_with_gold(_score_cache_for(labels, "101"), swapped)


# --- threat: manifest manipulation and path injection through shard IDs -----------------


@pytest.mark.parametrize(
    "shard_id", ["../../etc/x", "dev-0000/../x", "dev-00000", "DEV-0000", "", "dev-0000\n"]
)
def test_shard_ids_outside_the_builder_format_are_refused(shard_id: str) -> None:
    manifest = _manifest()
    manifest["shards"][0]["shard_id"] = shard_id
    _seal(manifest)
    with pytest.raises(ValueError, match="shard identity"):
        manifest_artifact.validate_manifest(manifest, code_sha=CODE_SHA)
    with pytest.raises(ValueError, match="shard IDs"):
        emit_matrix.emit_matrix(manifest)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda m: m.update(dataset_revision="other"), "immutable pin"),
        (lambda m: m.update(dataset_sha256="0" * 64), "immutable pin"),
        (lambda m: m.update(sample_count=99), "total record count"),
        (lambda m: m["shards"][0].update(count=1), "record count is inconsistent"),
        (lambda m: m["shards"][0]["record_ids"].__setitem__(0, "X" * 64), "invalid record"),
        (lambda m: m["shards"][0].update(record_ids_sha256="0" * 64), "record digest"),
        (lambda m: m.update(shards=[]), "at least one shard"),
    ],
)
def test_manifest_tampering_is_refused(mutate: Any, message: str) -> None:
    manifest = _manifest()
    mutate(manifest)
    _seal(manifest)
    with pytest.raises(ValueError, match=message):
        manifest_artifact.validate_manifest(manifest, code_sha=CODE_SHA)


def test_manifest_self_digest_is_checked() -> None:
    manifest = _manifest()
    manifest["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="manifest digest"):
        manifest_artifact.validate_manifest(manifest, code_sha=CODE_SHA)


def test_encrypted_manifest_round_trip_and_tampering(tmp_path: Path) -> None:
    key = secrets.token_bytes(32)
    metadata = manifest_artifact.manifest_metadata(run_id="101", code_sha=CODE_SHA)
    (tmp_path / "m.json").write_text(json.dumps(_manifest()), encoding="utf-8")
    manifest_artifact.encrypt_manifest_file(
        tmp_path / "m.json", tmp_path / "m.aesgcm", key=key, metadata=metadata
    )
    sealed = json.loads((tmp_path / "m.aesgcm").read_text(encoding="utf-8"))
    assert "record_ids" not in json.dumps(sealed)
    manifest_artifact.decrypt_manifest_file(
        tmp_path / "m.aesgcm", tmp_path / "out.json", key=key, expected_metadata=metadata
    )
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8")) == _manifest()
    cases = {
        "schema": {**sealed, "artifact_schema": "other"},
        "aead": {**sealed, "schema_version": "other"},
        "extra": {**sealed, "extra": 1},
        "metadata": {**sealed, "metadata": {**sealed["metadata"], "run_id": "102"}},
    }
    for name, envelope in cases.items():
        path = tmp_path / f"{name}.aesgcm"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with pytest.raises(ValueError):
            manifest_artifact.decrypt_manifest_file(
                path, tmp_path / f"{name}.json", key=key, expected_metadata=metadata
            )
        assert not (tmp_path / f"{name}.json").exists()
    wrong_run = manifest_artifact.manifest_metadata(run_id="102", code_sha=CODE_SHA)
    with pytest.raises(ValueError, match="metadata"):
        manifest_artifact.decrypt_manifest_file(
            tmp_path / "m.aesgcm", tmp_path / "x.json", key=key, expected_metadata=wrong_run
        )


def test_manifest_builder_resolves_duplicates_by_dec034_and_reports_counts_only() -> None:
    """DEC-034 A: one copy of each consistent repeat, conflicts excluded, counts only."""
    from scripts.benchmarks.phase1b.build_manifest import build_manifest

    rows = _rows()
    secret_doc = "UNIQUE-SENTINEL-DOCUMENT"
    rows[0] = {**rows[0], "doc": secret_doc}
    duplicated = [
        *rows,
        dict(rows[0]),  # exact copy
        dict(rows[0]),  # second exact copy
        {**rows[1], "label": "0" if rows[1]["label"] == "1" else "1"},  # label conflict
    ]
    manifest = build_manifest(
        duplicated,
        dataset_sha256=PIN["sha256"],
        dataset_revision=PIN["revision"],
        code_sha=CODE_SHA,
        shard_size=2,
    )
    assert manifest["identity_resolution"] == {
        "policy": common.DEDUP_POLICY,
        "source_rows": len(rows) + 3,
        "repeated_identities": 2,
        "duplicate_rows_removed": 2,
        "conflicting_identities_excluded": 1,
        "conflicting_rows_excluded": 2,
        "unique_identities_kept": len(rows) - 1,
    }
    selected = [rid for shard in manifest["shards"] for rid in shard["record_ids"]]
    assert sorted(selected) == sorted(
        common.stable_record_id(row) for row in rows if row is not rows[1]
    )
    assert common.stable_record_id(rows[1]) not in selected
    assert manifest["sample_count"] == len(rows) - 1
    encoded = common.canonical_json(manifest["identity_resolution"]).decode()
    assert secret_doc not in encoded and "claim" not in encoded


def test_manifest_builder_is_independent_of_duplicate_order() -> None:
    from scripts.benchmarks.phase1b.build_manifest import build_manifest

    rows = _rows()
    duplicated = [
        *rows,
        dict(rows[2]),
        {**rows[3], "label": "0" if rows[3]["label"] == "1" else "1"},
    ]
    kwargs = {
        "dataset_sha256": PIN["sha256"],
        "dataset_revision": PIN["revision"],
        "code_sha": CODE_SHA,
        "shard_size": 2,
    }
    assert build_manifest(duplicated, **kwargs) == build_manifest(
        list(reversed(duplicated)), **kwargs
    )


def test_manifest_builder_refuses_when_nothing_remains() -> None:
    from scripts.benchmarks.phase1b.build_manifest import build_manifest

    row = _rows(1)[0]
    with pytest.raises(ValueError, match="no DEV rows remain"):
        build_manifest(
            [row, {**row, "label": "1" if row["label"] == "0" else "0"}],
            dataset_sha256=PIN["sha256"],
            dataset_revision=PIN["revision"],
            code_sha=CODE_SHA,
        )
