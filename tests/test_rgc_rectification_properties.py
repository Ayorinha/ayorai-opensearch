"""Superseded text never supports a claim (Protocol Amendment 4, DEC-011 option A)."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_eval.py"))
Document = RUNNER["Document"]
Passage = RUNNER["Passage"]

OLD_TEXT = "A tarifa fictícia era de 10 por cento."
NEW_TEXT = "Retificação: a tarifa fictícia era de 12 por cento."


def _document(source_id: str, text: str, superseded: tuple[Any, ...] = ()) -> Any:
    return Document(
        source_id=source_id,
        source_url=f"https://example.test/{source_id}",
        retrieved_at="2026-01-01T00:00:00Z",
        text=text,
        source_license="synthetic",
        superseded_spans=superseded,
    )


def test_superseded_text_cannot_support_a_rectified_claim() -> None:
    old = _document("synthetic-old-version", OLD_TEXT, ((0, len(OLD_TEXT), "synthetic-new"),))
    case: dict[str, Any] = {"case_id": "synthetic-rectification-001", "rectified": True}
    assert RUNNER["case_rectified"](case) is True

    prediction = RUNNER["predict"](
        "A tarifa fictícia era de 10 por cento.",
        [Passage("synthetic-old-version", 0, len(OLD_TEXT))],
        {"synthetic-old-version": old},
    )

    assert prediction["judge_verdict"] != "SUPPORTED"
    assert prediction["evidence"] == []
    assert prediction["excluded_superseded_passages"] == [
        {"document_id": "synthetic-old-version", "start_offset": 0, "end_offset": len(OLD_TEXT)}
    ]


def test_the_same_text_still_supports_when_not_superseded() -> None:
    # Control: without the rectification mark the passage is evidence as before.
    current = _document("synthetic-current", OLD_TEXT)
    prediction = RUNNER["predict"](
        "A tarifa fictícia era de 10 por cento.",
        [Passage("synthetic-current", 0, len(OLD_TEXT))],
        {"synthetic-current": current},
    )
    assert prediction["judge_verdict"] == "SUPPORTED"
    assert prediction["excluded_superseded_passages"] == []


def test_only_passages_touching_a_superseded_span_are_excluded() -> None:
    text = OLD_TEXT + " " + NEW_TEXT
    start = len(OLD_TEXT) + 1
    document = _document("synthetic-gazette", text, ((0, len(OLD_TEXT), "synthetic-gazette"),))
    prediction = RUNNER["predict"](
        "A tarifa fictícia era de 12 por cento.",
        [
            Passage("synthetic-gazette", 5, len(OLD_TEXT) + 3),  # partial overlap
            Passage("synthetic-gazette", start, len(text)),
        ],
        {"synthetic-gazette": document},
    )
    assert prediction["evidence"] == [
        {"document_id": "synthetic-gazette", "start_offset": start, "end_offset": len(text)}
    ]
    assert len(prediction["excluded_superseded_passages"]) == 1


def _write_corpus(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    path = tmp_path / "documents.jsonl"
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _record(source_id: str, text: str, **extra: Any) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_url": f"https://example.test/{source_id}",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "source_license": "synthetic",
        "text": text,
        **extra,
    }


def test_loader_reads_superseded_spans(tmp_path: Path) -> None:
    path = _write_corpus(
        tmp_path,
        [
            _record(
                "old",
                OLD_TEXT,
                superseded_spans=[{"start": 0, "end": 10, "superseded_by": "new"}],
            ),
            _record("new", NEW_TEXT),
        ],
    )
    documents = RUNNER["load_documents"](path)
    assert documents["old"].superseded_spans == ((0, 10, "new"),)
    assert documents["new"].superseded_spans == ()


@pytest.mark.parametrize(
    ("spans", "message"),
    [
        ("not-a-list", "must be a list"),
        ([{"start": 0, "end": 5}], "exactly start, end and superseded_by"),
        ([{"start": 5, "end": 5, "superseded_by": "new"}], "outside the text"),
        ([{"start": 0, "end": 10_000, "superseded_by": "new"}], "outside the text"),
        ([{"start": True, "end": 5, "superseded_by": "new"}], "outside the text"),
        ([{"start": 0, "end": 5, "superseded_by": " "}], "non-empty source_id"),
        (
            [
                {"start": 0, "end": 6, "superseded_by": "new"},
                {"start": 5, "end": 9, "superseded_by": "new"},
            ],
            "must not overlap",
        ),
        ([{"start": 0, "end": 5, "superseded_by": "missing"}], "not a document of the corpus"),
    ],
)
def test_loader_rejects_malformed_superseded_spans(
    tmp_path: Path, spans: Any, message: str
) -> None:
    path = _write_corpus(
        tmp_path,
        [_record("old", OLD_TEXT, superseded_spans=spans), _record("new", NEW_TEXT)],
    )
    with pytest.raises(ValueError, match=message):
        RUNNER["load_documents"](path)
