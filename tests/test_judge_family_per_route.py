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
    # /v1/check and /v2/audit adjudicate through this pipeline (/v1/fields does not:
    # see test_fields_route_uses_no_judge).
    assert claim_pipeline.judge is adr002_judge.judge


def test_document_check_routes_do_not_import_judge2() -> None:
    for module in ("document_check.py", "claim_pipeline.py"):
        imported = _imported_modules(SRC / module)
        assert not any("judge2" in name for name in imported), (
            f"{module} imports Judge 2.0; migrating a 1.x route needs its own ADR (ADR-011 §4)"
        )


def test_fields_route_uses_no_judge() -> None:
    # AP1: /v1/fields compares typed field values with field_check and returns its own
    # vocabulary (conforme, divergente, ambiguo, ausente, invalido). It uses neither
    # the ADR-002 Judge nor Judge 2.0, unlike what the ADR-011 table states.
    imported = _imported_modules(SRC / "field_check.py")
    assert not any(
        name.endswith("judge") or "judge2" in name or "document_check" in name for name in imported
    )


def test_fields_outcome_vocabulary_is_closed() -> None:
    from fastapi.testclient import TestClient

    from ayorai_attractor.api.app import app

    response = TestClient(app).post(
        "/v1/fields",
        json={
            "document": {"id": "d0", "text": "Valor total: R$ 1.500,00. Data: 10/03/2024."},
            "fields": [
                {"name": "valor", "type": "money", "value": "1500,00", "labels": ["Valor total"]}
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["summary"]) == {"conforme", "divergente", "ambiguo", "ausente", "invalido"}
    assert "verdict" not in str(body["results"])
