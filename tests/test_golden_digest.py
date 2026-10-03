from ayorai_attractor.evaluation.golden import _content_digest


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
