#!/usr/bin/env python3
"""Reproduce the project's frozen evidence with one command.

Runs, in order, the same deterministic checks that the required CI gates run
(golden-smoke, golden-regression, judge-regression, Golden r2 migration
determinism) and, unless ``--quick`` is given, the full test suite. Every
expected value below is copied from ``.github/workflows/ci.yml``; the test
``tests/test_reproduce_script.py`` fails if the two drift apart.

The script only reads frozen artifacts and writes reports under ``reports/``.
It never edits fixtures, Golden files, manifests or hashes.

Usage::

    make reproduce            # full run, including pytest
    python scripts/reproduce.py --quick   # skip pytest
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

# Expected values — must match .github/workflows/ci.yml (guarded by a test).
SMOKE_SEMANTIC_SHA256 = "969ec61a4aee4e4426f5d217819bd185ebba248743e7721714a3123f5df67c3d"
GOLDEN_V0_SEMANTIC_SHA256 = "21abb816facce73fc924842d12b373b8792abc2e7389e129c35bb58bab806632"
GOLDEN_V01_SEMANTIC_SHA256 = "64f743b3e87553b2eca207cbb60a0ae8f87d619bc968c8ed562f8048f1529608"

GOLDEN_V0_EXPECTED: dict[str, Any] = {
    "case_count": 34,
    "corpus_document_count": 52,
    "cases_with_global_verdict": 30,
    "global_accuracy": {"correct": 7, "total": 30, "accuracy": 0.233333},
    "balanced_accuracy": 0.42735,
    "legacy_accuracy": {"correct": 13, "total": 30, "accuracy": 0.433333},
    "semantic_digest_version": "1",
    "semantic_sha256": GOLDEN_V0_SEMANTIC_SHA256,
}
GOLDEN_V0_MCNEMAR = {
    "legacy_correct_new_wrong": 10,
    "new_correct_legacy_wrong": 4,
    "exact_p": 0.1795654296875,
}
GOLDEN_V01_EXPECTED: dict[str, Any] = {
    "case_count": 34,
    "corpus_document_count": 52,
    "cases_with_global_verdict": 30,
    "global_accuracy": {"correct": 10, "total": 30, "accuracy": 0.333333},
    "balanced_accuracy": 0.481838,
    "legacy_accuracy": {"correct": 13, "total": 30, "accuracy": 0.433333},
    "semantic_digest_version": "1",
    "semantic_sha256": GOLDEN_V01_SEMANTIC_SHA256,
}
GOLDEN_V01_MCNEMAR = {
    "legacy_correct_new_wrong": 9,
    "new_correct_legacy_wrong": 6,
    "exact_p": 0.60723876953125,
}


class CheckFailed(RuntimeError):
    """Raised when an observed value differs from the frozen expectation."""


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise CheckFailed(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout


def _expect(report: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    for key, value in expected.items():
        if report.get(key) != value:
            raise CheckFailed(f"{label}: {key} = {report.get(key)!r}, expected {value!r}")


def _eval_suite(suite: str, out: Path) -> dict[str, Any]:
    _run(["attractor", "eval", "--suite", suite, "--out", str(out)])
    data: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
    if len(data.get("content_sha256", "")) != 64:
        raise CheckFailed(f"{suite}: content_sha256 missing or malformed")
    return data


def check_golden_lint() -> str:
    _run([sys.executable, "scripts/lint_golden.py"])
    return "frozen Golden v0 contract valid"


def check_smoke() -> str:
    r = _eval_suite("smoke-v0", REPORTS / "reproduce-smoke-v0.json")
    _expect(
        r,
        {"case_count": 5, "semantic_digest_version": "1", "semantic_sha256": SMOKE_SEMANTIC_SHA256},
        "smoke-v0",
    )
    return f"5 cases, semantic_sha256={r['semantic_sha256'][:12]}…"


def check_golden_v0() -> str:
    r = _eval_suite("golden-v0", REPORTS / "reproduce-golden-v0.json")
    _expect(r, GOLDEN_V0_EXPECTED, "golden-v0")
    _expect(r["mcnemar_vs_legacy"], GOLDEN_V0_MCNEMAR, "golden-v0 McNemar")
    if r["majority_class_baseline"]["accuracy"] != 0.433333:
        raise CheckFailed("golden-v0: majority-class baseline changed")
    return f"accuracy {r['global_accuracy']['accuracy']}, balanced {r['balanced_accuracy']}"


def check_golden_v01() -> str:
    r = _eval_suite("golden-v0.1", REPORTS / "reproduce-golden-v0.1.json")
    _expect(r, GOLDEN_V01_EXPECTED, "golden-v0.1")
    _expect(r["mcnemar_vs_legacy"], GOLDEN_V01_MCNEMAR, "golden-v0.1 McNemar")
    return f"accuracy {r['global_accuracy']['accuracy']}, balanced {r['balanced_accuracy']}"


def check_judge() -> str:
    from ayorai_attractor.evaluation.judge import evaluate_judge_suite

    r = evaluate_judge_suite(ROOT / "evals/judge/v0.jsonl")
    if (r["case_count"], r["correct"], r["accuracy"]) != (6, 6, 1.0):
        raise CheckFailed(f"judge v0: {r['correct']}/{r['case_count']}")
    smoke = evaluate_judge_suite(ROOT / "evals/golden/judge-smoke.jsonl")
    if smoke["case_count"] != 1 or smoke["correct"] != 1:
        raise CheckFailed("judge smoke failed")
    if smoke["results"][0]["predicted"] != "SUPPORTED":
        raise CheckFailed("judge smoke: predicted verdict changed")
    return "judge v0 6/6, judge smoke 1/1"


def check_r2_migration() -> str:
    _run([sys.executable, "scripts/migrate_golden_r2.py", "--check-determinism"])
    return "derived Golden r2 migration is deterministic"


def check_pytest() -> str:
    out = _run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider"])
    tail = [line for line in out.splitlines() if "passed" in line]
    return tail[-1].strip() if tail else "pytest passed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="skip the full pytest run")
    args = parser.parse_args(argv)

    REPORTS.mkdir(exist_ok=True)
    checks: list[tuple[str, Callable[[], str]]] = [
        ("golden-lint", check_golden_lint),
        ("golden-smoke", check_smoke),
        ("golden-v0", check_golden_v0),
        ("golden-v0.1", check_golden_v01),
        ("judge-regression", check_judge),
        ("golden-r2-migration", check_r2_migration),
    ]
    if not args.quick:
        checks.append(("pytest", check_pytest))

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    results: list[dict[str, Any]] = []
    failed = False
    for name, fn in checks:
        start = time.monotonic()
        try:
            detail, ok = fn(), True
        except CheckFailed as exc:
            detail, ok, failed = str(exc), False, True
        elapsed = round(time.monotonic() - start, 2)
        results.append({"check": name, "ok": ok, "seconds": elapsed, "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'}  {name:<20} {elapsed:>6.2f}s  {detail.splitlines()[0]}")

    summary = {
        "commit": commit or None,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "quick": args.quick,
        "all_passed": not failed,
        "results": results,
    }
    out = REPORTS / "reproduce-summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{'ALL CHECKS PASSED' if not failed else 'SOME CHECKS FAILED'} — summary: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
