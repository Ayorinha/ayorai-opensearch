"""P4-01: the NLTK segmentation equivalence harness is deterministic and fails closed.

The harness itself runs under two separate NLTK installs (see
docs/audit/P4-NLTK-EQUIVALENCE-2026-11-28.md); these tests cover the parts that do not
need NLTK: the corpus is reproducible, holds no benchmark data, and any difference
makes the comparison fail.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.benchmarks.phase1b import nltk_equivalence as eq


def test_corpus_is_deterministic_and_has_no_benchmark_source() -> None:
    first, second = eq.corpus(), eq.corpus()
    assert first == second
    assert {source for source, _ in first} == {"edge", "repository", "synthetic"}
    assert sum(1 for source, _ in first if source == "synthetic") == eq.SYNTHETIC_COUNT


def _report(digests: list[str]) -> dict[str, Any]:
    texts = eq.corpus()[: len(digests)]
    rows = [
        {
            "index": i,
            "source": source,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "sent_tokenize": d,
            "word_tokenize": d,
            "words_per_sentence": d,
        }
        for i, ((source, text), d) in enumerate(zip(texts, digests, strict=True))
    ]
    return {
        "nltk_version": "x",
        "items": len(rows),
        "corpus_sha256": "same",
        "rows": rows,
    }


def test_identical_reports_are_equivalent() -> None:
    result = eq.compare(_report(["a", "b", "c"]), _report(["a", "b", "c"]))
    assert all(result["equivalent"].values())
    assert result["difference_counts"] == {
        "sent_tokenize": 0,
        "word_tokenize": 0,
        "words_per_sentence": 0,
    }


def test_a_single_difference_breaks_equivalence() -> None:
    result = eq.compare(_report(["a", "b", "c"]), _report(["a", "X", "c"]))
    assert result["equivalent"] == {
        "sent_tokenize": False,
        "word_tokenize": False,
        "words_per_sentence": False,
    }
    assert [row["index"] for row in result["examples"]["sent_tokenize"]] == [1]


def test_reports_on_different_corpora_are_refused() -> None:
    other = _report(["a"])
    other["corpus_sha256"] = "different"
    with pytest.raises(SystemExit):
        eq.compare(_report(["a"]), other)


def test_compare_cli_exits_non_zero_on_difference(tmp_path: Path) -> None:
    baseline, candidate = tmp_path / "a.json", tmp_path / "b.json"
    baseline.write_text(json.dumps(_report(["a", "b"])), encoding="utf-8")
    candidate.write_text(json.dumps(_report(["a", "c"])), encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        import sys

        argv = sys.argv
        sys.argv = ["nltk_equivalence.py", "--compare", str(baseline), str(candidate)]
        try:
            eq.main()
        finally:
            sys.argv = argv
    assert caught.value.code == 1
