from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_eval.py"))
Document = RUNNER["Document"]
Passage = RUNNER["Passage"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "case_rectified currently marks the reporting stratum only; "
        "the runner does not yet exclude superseded passages from adjudication"
    ),
)
def test_superseded_text_cannot_support_a_rectified_claim() -> None:
    """Synthetic characterization of the unresolved rectification invariant."""
    old_text = "A tarifa fictícia era de 10 por cento."
    old_document = Document(
        source_id="synthetic-old-version",
        source_url="https://example.test/synthetic-old-version",
        retrieved_at="2026-01-01T00:00:00Z",
        text=old_text,
        source_license="synthetic",
    )
    case: dict[str, Any] = {
        "case_id": "synthetic-rectification-001",
        "rectified": True,
    }

    assert RUNNER["case_rectified"](case) is True

    prediction = RUNNER["predict"](
        "A tarifa fictícia era de 10 por cento.",
        [Passage("synthetic-old-version", 0, len(old_text))],
        {"synthetic-old-version": old_document},
    )

    assert prediction["judge_verdict"] != "SUPPORTED"
