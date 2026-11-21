"""ADR-011: each route uses exactly one Judge rule family."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

# The package re-exports a ``judge`` function that shadows the submodule name.
claim_pipeline = importlib.import_module("ayorai_attractor.verification.claim_pipeline")
adr002_judge = importlib.import_module("ayorai_attractor.verification.judge")

SRC = Path(__file__).resolve().parents[1] / "src" / "ayorai_attractor" / "verification"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            modules.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def test_check_pipeline_uses_the_adr002_judge() -> None:
    # /v1/check, /v1/fields and /v2/audit adjudicate through this pipeline.
    assert claim_pipeline.judge is adr002_judge.judge


def test_document_check_routes_do_not_import_judge2() -> None:
    for module in ("document_check.py", "claim_pipeline.py"):
        imported = _imported_modules(SRC / module)
        assert not any("judge2" in name for name in imported), (
            f"{module} imports Judge 2.0; migrating a 1.x route needs its own ADR (ADR-011 §4)"
        )
