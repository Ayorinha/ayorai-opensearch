"""Synthetic-only fixtures; no dataset examples or real text are included."""

import json

import pytest

from ayorai_attractor.evaluation.international import (
    DatasetError,
    adapt_records,
    evaluate,
)

MAPPING = {
    "schema_version": "1.0.0",
    "mapping_id": "llm-aggrefact-label-map-v1",
    "native_binary_labels": {"1": "SUPPORTED", "0": "NOT_SUPPORTED"},
}


def test_synthetic_fixture_preserves_native_binary_negative() -> None:
    fixture = [
        {
            "doc": "SYNTHETIC document A.",
            "claim": "SYNTHETIC claim A.",
            "label": 1,
            "dataset": "SYNTHETIC-A",
        },
        {
            "doc": "SYNTHETIC document B.",
            "claim": "SYNTHETIC claim B.",
            "label": 0,
            "dataset": "SYNTHETIC-B",
        },
    ]
    adapted = adapt_records(fixture, MAPPING)
    assert [item["label"] for item in adapted] == ["SUPPORTED", "NOT_SUPPORTED"]
    assert all("SYNTHETIC" in item["doc"] for item in adapted)


@pytest.mark.parametrize(
    "record",
    [
        {
            "doc": "SYNTHETIC doc",
            "claim": "SYNTHETIC claim",
            "label": 2,
            "dataset": "SYNTHETIC",
        },
        {
            "doc": "",
            "claim": "SYNTHETIC claim",
            "label": 1,
            "dataset": "SYNTHETIC",
        },
        {
            "doc": "SYNTHETIC doc",
            "claim": "SYNTHETIC claim",
            "label": 1,
        },
    ],
)
def test_invalid_synthetic_rows_fail_not_silently_drop(record: dict) -> None:
    with pytest.raises(DatasetError):
        adapt_records([record], MAPPING)


def test_report_records_cli_sha_provenance(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ayorai_attractor.evaluation.international as harness

    data = [
        {
            "doc": "SYNTHETIC document supporting claim.",
            "claim": "SYNTHETIC claim one.",
            "label": 1,
            "dataset": "SYNTHETIC-main",
        },
        {
            "doc": "SYNTHETIC document contradicting claim.",
            "claim": "SYNTHETIC claim two.",
            "label": 0,
            "dataset": "ragtruth",
        },
    ]
    dataset_path = tmp_path / "fixture.jsonl"
    dataset_path.write_text("\n".join(json.dumps(row) for row in data) + "\n", encoding="utf-8")
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(json.dumps(MAPPING), encoding="utf-8")

    monkeypatch.setattr(
        harness,
        "predict",
        lambda row, detector: (
            row["label"],
            "SUPPORTS" if row["label"] == "SUPPORTED" else "REFUTES",
        ),
    )
    report = evaluate(
        dataset_path,
        mapping_path,
        tmp_path / "report.json",
        tmp_path / "report.md",
        code_sha="synthetic-test-sha",
    )
    assert report["code_sha"] == "synthetic-test-sha"
    assert report["code_sha_source"] == "cli_argument"
    assert report["evaluated_component"].startswith("RuleStanceDetector")
    assert report["end_to_end_attractor"] is False
    assert report["response_policy_abstentions"]["value"] is None
    assert report["unverified_verdict_count"]["value"] is None
