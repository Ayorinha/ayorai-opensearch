"""P4-01: the vendored nltk 3.9.4 segmentation used by the Phase 1b shards.

Exact equivalence with nltk 3.9.4 is checked against the pinned punkt_tab data in CI
(``phase1b-inference-lock`` job) and here when ``PHASE1B_PUNKT_TAB_DIR`` points to a
verified data directory; the other tests need no data.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from scripts.benchmarks.phase1b import nltk_equivalence, nltk_resources, vendor_nltk

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase1b_nltk394_segmentation.json"


def _tiny_punkt(data_dir: Path, abbreviations: str = "dr\nmr\n") -> Path:
    lang = data_dir / "tokenizers" / "punkt_tab" / "english"
    lang.mkdir(parents=True)
    (lang / "abbrev_types.txt").write_text(abbreviations, encoding="utf-8")
    (lang / "collocations.tab").write_text("", encoding="utf-8")
    (lang / "sent_starters.txt").write_text("he\n", encoding="utf-8")
    (lang / "ortho_context.tab").write_text("he\t2\n", encoding="utf-8")
    return data_dir


def test_tokenizers_need_a_configured_data_dir(tmp_path: Path) -> None:
    vendor_nltk.configure(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        vendor_nltk.sent_tokenize("One. Two.")
    vendor_nltk._data_dir = None
    vendor_nltk._punkt.cache_clear()
    with pytest.raises(RuntimeError, match="configure"):
        vendor_nltk.sent_tokenize("One. Two.")


def test_segmentation_uses_the_configured_punkt_parameters(tmp_path: Path) -> None:
    vendor_nltk.configure(_tiny_punkt(tmp_path))
    assert vendor_nltk.sent_tokenize("Dr. Smith left. He came back.") == [
        "Dr. Smith left.",
        "He came back.",
    ]
    assert vendor_nltk.word_tokenize("He said: 'It's John's book.'") == [
        "He", "said", ":", "'It", "'s", "John", "'s", "book", ".", "'",
    ]  # fmt: skip
    # Training is not vendored: only the tokenizer with loaded parameters is.
    with pytest.raises(NotImplementedError):
        vendor_nltk.punkt.PunktSentenceTokenizer("some training text")


def test_prepare_runtime_checks_the_pin_and_configures_the_vendored_tokenizers(
    tmp_path: Path,
) -> None:
    pin = nltk_resources.load_pin(ROOT / "configs" / "benchmarks" / "nltk-punkt-tab-pin.json")
    assert pin["nltk_version"] == vendor_nltk.NLTK_VERSION
    with pytest.raises(RuntimeError, match="version"):
        nltk_resources.prepare_runtime({**pin, "nltk_version": "3.10.4"}, tmp_path)
    with pytest.raises(ValueError, match="missing"):
        nltk_resources.prepare_runtime(pin, tmp_path)


def test_the_shard_imports_no_nltk_package() -> None:
    source = (ROOT / "scripts" / "benchmarks" / "phase1b" / "run_shard.py").read_text("utf-8")
    assert not re.search(r"^\s*(from nltk[ .]|import nltk\b)", source, re.MULTILINE)


@pytest.mark.skipif(
    not os.environ.get("PHASE1B_PUNKT_TAB_DIR"),
    reason="set PHASE1B_PUNKT_TAB_DIR to a verified punkt_tab data directory",
)
def test_vendored_segmentation_reproduces_nltk_394(tmp_path: Path) -> None:
    report = nltk_equivalence.run(
        Path(os.environ["PHASE1B_PUNKT_TAB_DIR"]), implementation="vendored", kind="fixed"
    )
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert report["corpus_sha256"] == expected["corpus_sha256"]
    assert report["results_sha256"] == expected["results_sha256"]
