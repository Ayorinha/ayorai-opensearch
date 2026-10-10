import os
import subprocess
import sys
from pathlib import Path

from ayorai_attractor.evaluation.digest import semantic_sha256
from ayorai_attractor.evaluation.golden import _content_digest, evaluate_golden_v0


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _evaluate(suite: str = "golden-v0") -> dict[str, object]:
    root = _root()
    golden_name = "v0.1.jsonl" if suite == "golden-v0.1" else "v0.jsonl"
    return evaluate_golden_v0(
        root / "evals" / "golden" / golden_name,
        root / "evals" / "corpus" / "documents.jsonl",
        suite=suite,
    )


def test_content_digest_ignores_volatile_runtime_fields() -> None:
    report = {
        "suite": "golden-v0",
        "global_accuracy": {"correct": 1, "total": 1, "accuracy": 1.0},
        "latency_ms": {"p50": 10.0, "p95": 20.0},
        "git_sha": "first",
    }
    first = _content_digest(report)
    report["latency_ms"]["p95"] = 999.0
    report["git_sha"] = "second"
    assert _content_digest(report) == first


def test_content_digest_changes_for_semantic_results() -> None:
    report = {
        "suite": "golden-v0",
        "global_accuracy": {"correct": 1, "total": 1, "accuracy": 1.0},
    }
    first = _content_digest(report)
    report["global_accuracy"]["correct"] = 0
    report["global_accuracy"]["accuracy"] = 0.0
    assert _content_digest(report) != first


def test_semantic_digest_uses_canonical_utf8_json() -> None:
    report = {"semantic_digest_version": "1", "claim": "ação"}
    assert (
        semantic_sha256(report)
        == "fd0460a3f7bb1170bb31cbf90708f350fd87059e07a21f9e13ee4551cb85565e"
    )


def test_semantic_digest_recursively_ignores_execution_metadata() -> None:
    report = {
        "semantic_digest_version": "1",
        "suite": "golden-v0",
        "global_accuracy": {"correct": 1, "total": 1, "accuracy": 1.0},
        "results": [
            {
                "predicted": "SUPPORTED",
                "latency_ms": 10.0,
                "git_sha": "first",
                "nested": {"semantic_sha256": "first", "metric": 0.75},
            }
        ],
    }
    first = semantic_sha256(report)
    report["results"][0]["latency_ms"] = 999.0
    report["results"][0]["git_sha"] = "second"
    report["results"][0]["nested"]["semantic_sha256"] = "second"
    assert semantic_sha256(report) == first


def test_semantic_digest_changes_when_evidence_dates_change_at_any_level() -> None:
    for field in ("retrieved_at", "published_at", "collected_at"):
        top_level = {"semantic_digest_version": "1", field: "2026-01-01"}
        first_top_level = semantic_sha256(top_level)
        top_level[field] = "2020-05-05"
        assert semantic_sha256(top_level) != first_top_level, field

        nested = {
            "semantic_digest_version": "1",
            "results": [{"evidence": {field: "2026-01-01"}}],
        }
        first_nested = semantic_sha256(nested)
        nested["results"][0]["evidence"][field] = "2020-05-05"
        assert semantic_sha256(nested) != first_nested, field


def test_semantic_digest_ignores_only_explicit_volatile_keys_recursively() -> None:
    report = {
        "semantic_digest_version": "1",
        "latency_ms": 10,
        "results": [
            {
                "latency_ms": 20,
                "git_sha": "first",
                "content_sha256": "legacy-first",
                "semantic_sha256": "semantic-first",
                "evidence": {"latency_ms": 30, "retrieved_at": "2026-01-01"},
            }
        ],
    }
    first = semantic_sha256(report)
    report["latency_ms"] = 999
    result = report["results"][0]
    result["latency_ms"] = 888
    result["git_sha"] = "second"
    result["content_sha256"] = "legacy-second"
    result["semantic_sha256"] = "semantic-second"
    result["evidence"]["latency_ms"] = 777
    assert semantic_sha256(report) == first


def test_semantic_digest_changes_when_prediction_or_metric_changes() -> None:
    report = {
        "semantic_digest_version": "1",
        "results": [{"id": "case-1", "predicted": "SUPPORTED"}],
        "global_accuracy": {"correct": 1, "total": 1, "accuracy": 1.0},
    }
    first = semantic_sha256(report)
    report["results"][0]["predicted"] = "REFUTED"
    assert semantic_sha256(report) != first
    report["results"][0]["predicted"] = "SUPPORTED"
    report["global_accuracy"]["accuracy"] = 0.5
    assert semantic_sha256(report) != first


def test_semantic_digest_is_stable_for_repeated_suite_runs_in_one_process() -> None:
    first = _evaluate("smoke-v0")
    second = _evaluate("smoke-v0")
    assert first["semantic_digest_version"] == "1"
    assert len(first["semantic_sha256"]) == 64
    assert first["semantic_sha256"] == second["semantic_sha256"]


def test_semantic_digest_is_stable_across_subprocess_runs() -> None:
    script = (
        "from pathlib import Path; "
        "from ayorai_attractor.evaluation.golden import evaluate_golden_v0; "
        "root = Path.cwd(); "
        "r = evaluate_golden_v0(root / 'evals/golden/v0.jsonl', "
        "root / 'evals/corpus/documents.jsonl', suite='smoke-v0'); "
        "print(r['semantic_sha256'])"
    )
    root = _root()
    env = os.environ.copy()
    env.pop("GITHUB_SHA", None)
    digests = [
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for _ in range(2)
    ]
    assert len(digests[0]) == 64
    assert digests[0] == digests[1]


def test_report_preserves_legacy_content_digest_semantics() -> None:
    report = _evaluate("smoke-v0")
    legacy_payload = {
        key: value
        for key, value in report.items()
        if key not in {"content_sha256", "semantic_digest_version", "semantic_sha256"}
    }
    assert report["content_sha256"] == _content_digest(legacy_payload)
    assert report["semantic_sha256"] == semantic_sha256(report)


def test_commit_base_metric_references_remain_unchanged() -> None:
    references = {
        "golden-v0": {
            "correct": 7,
            "accuracy": 0.233333,
            "balanced_accuracy": 0.42735,
            "legacy_correct": 13,
            "legacy_correct_new_wrong": 10,
            "new_correct_legacy_wrong": 4,
            "mcnemar_p": 0.1795654296875,
        },
        "golden-v0.1": {
            "correct": 10,
            "accuracy": 0.333333,
            "balanced_accuracy": 0.481838,
            "legacy_correct": 13,
            "legacy_correct_new_wrong": 9,
            "new_correct_legacy_wrong": 6,
            "mcnemar_p": 0.60723876953125,
        },
    }
    for suite, expected in references.items():
        report = _evaluate(suite)
        assert report["global_accuracy"]["correct"] == expected["correct"]
        assert report["global_accuracy"]["total"] == 30
        assert report["global_accuracy"]["accuracy"] == expected["accuracy"]
        assert report["balanced_accuracy"] == expected["balanced_accuracy"]
        assert report["legacy_accuracy"]["correct"] == expected["legacy_correct"]
        assert report["legacy_accuracy"]["total"] == 30
        assert (
            report["mcnemar_vs_legacy"]["legacy_correct_new_wrong"]
            == expected["legacy_correct_new_wrong"]
        )
        assert (
            report["mcnemar_vs_legacy"]["new_correct_legacy_wrong"]
            == expected["new_correct_legacy_wrong"]
        )
        assert report["mcnemar_vs_legacy"]["exact_p"] == expected["mcnemar_p"]
        assert report["semantic_digest_version"] == "1"
        assert len(report["semantic_sha256"]) == 64
