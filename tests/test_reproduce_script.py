"""Guard: scripts/reproduce.py must expect exactly what the CI gates expect."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")


def _load():
    spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts/reproduce.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_semantic_hashes_match_ci() -> None:
    mod = _load()
    for digest in (
        mod.SMOKE_SEMANTIC_SHA256,
        mod.GOLDEN_V0_SEMANTIC_SHA256,
        mod.GOLDEN_V01_SEMANTIC_SHA256,
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
        assert digest in CI, f"{digest} not found in ci.yml"


def test_ci_hashes_all_covered_by_script() -> None:
    mod = _load()
    ci_hashes = set(re.findall(r"semantic_sha256['\"]\]\s*==\s*['\"]([0-9a-f]{64})", CI))
    script_hashes = {
        mod.SMOKE_SEMANTIC_SHA256,
        mod.GOLDEN_V0_SEMANTIC_SHA256,
        mod.GOLDEN_V01_SEMANTIC_SHA256,
    }
    assert ci_hashes == script_hashes


def test_metric_expectations_match_ci() -> None:
    mod = _load()
    for expected in (mod.GOLDEN_V0_EXPECTED, mod.GOLDEN_V01_EXPECTED):
        acc = expected["global_accuracy"]
        literal = (
            f'{{"correct": {acc["correct"]}, "total": {acc["total"]}, '
            f'"accuracy": {acc["accuracy"]}}}'
        )
        assert literal in CI
        assert f'r["balanced_accuracy"] == {expected["balanced_accuracy"]}' in CI
    for mcnemar in (mod.GOLDEN_V0_MCNEMAR, mod.GOLDEN_V01_MCNEMAR):
        for key, value in mcnemar.items():
            assert f'["{key}"] == {value}' in CI


def test_makefile_exposes_reproduce() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "reproduce:\n\tpython scripts/reproduce.py\n" in makefile
