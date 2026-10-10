import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals/golden/legacy-baseline-v0.jsonl"
MANIFEST = ROOT / "evals/golden/MANIFEST.json"
EXPECTED_IDS = (
    "f01", "f02", "f03", "f04", "m01", "m02", "m03", "c01", "c02", "c03",
    "x01", "x02", "x03", "n01", "n02", "i01", "i02", "i03", "o01", "o02",
    "r01", "r02", "h01", "ch01", "p01", "p02", "x04", "x05", "x06", "rf01",
    "i04", "nt01", "nt02", "nt03",
)
ABSTENTIONS = {"n01", "n02", "o01", "o02"}


def _records() -> list[dict[str, str]]:
    return [
        json.loads(line)
        for line in BASELINE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_legacy_baseline_hash_matches_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["legacy_baseline"]["files"]["evals/golden/legacy-baseline-v0.jsonl"]["sha256"]
    assert hashlib.sha256(BASELINE.read_bytes()).hexdigest() == expected


def test_legacy_baseline_has_exactly_68_unique_suite_case_keys() -> None:
    records = _records()
    keys = [(record["suite"], record["case_id"]) for record in records]
    assert len(records) == 68
    assert len(set(keys)) == 68
    for suite in ("golden-v0", "golden-v0.1"):
        suite_records = [record for record in records if record["suite"] == suite]
        assert [record["case_id"] for record in suite_records] == list(EXPECTED_IDS)
        assert sum(record["prediction"] == "PARTIALLY_SUPPORTED" for record in suite_records) == 30
        assert {
            record["case_id"] for record in suite_records
            if record["prediction"] == "UNVERIFIED"
        } == ABSTENTIONS


def test_legacy_baseline_historical_metrics_remain_coherent() -> None:
    records = _records()
    for suite, relative_path in (
        ("golden-v0", "evals/golden/v0.jsonl"),
        ("golden-v0.1", "evals/golden/v0.1.jsonl"),
    ):
        predictions = {
            record["case_id"]: record["prediction"]
            for record in records if record["suite"] == suite
        }
        cases = [
            json.loads(line)
            for line in (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        global_cases = [case for case in cases if "global" in case]
        abstain_cases = [case for case in cases if "response_status" in case]
        assert len(global_cases) == 30
        assert sum(str(case["global"]).upper() == predictions[str(case["id"])] for case in global_cases) == 13
        assert len(abstain_cases) == 4
        assert sum(
            str(case["response_status"]).upper() == predictions[str(case["id"])]
            for case in abstain_cases
        ) == 0


def test_semantic_digests_are_unchanged_for_all_three_suites() -> None:
    from ayorai_attractor.evaluation.golden import evaluate_golden_v0

    expected = {
        "golden-v0": "21abb816facce73fc924842d12b373b8792abc2e7389e129c35bb58bab806632",
        "golden-v0.1": "64f743b3e87553b2eca207cbb60a0ae8f87d619bc968c8ed562f8048f1529608",
        "smoke-v0": "969ec61a4aee4e4426f5d217819bd185ebba248743e7721714a3123f5df67c3d",
    }
    for suite, golden_name in (
        ("golden-v0", "v0.jsonl"),
        ("golden-v0.1", "v0.1.jsonl"),
        ("smoke-v0", "v0.jsonl"),
    ):
        report = evaluate_golden_v0(
            ROOT / "evals/golden" / golden_name,
            ROOT / "evals/corpus/documents.jsonl",
            suite=suite,
        )
        assert report["semantic_sha256"] == expected[suite]
