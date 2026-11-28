"""NLTK 3.9.4 sentence and word segmentation, vendored for the Phase 1b inference jobs.

The shards only call ``sent_tokenize`` and ``word_tokenize`` (``run_shard``). Installing
nltk 3.9.4 for that brought 31 published high/critical advisories into the job that
holds the artifact key, and nltk 3.10.4 segments differently (see
docs/audit/P4-NLTK-EQUIVALENCE-2026-11-28.md). This package keeps the 3.9.4 behaviour
with only the code those two functions run; README.md lists the edits.
"""

from __future__ import annotations

import functools
from pathlib import Path

from .destructive import NLTKWordTokenizer
from .punkt import PunktTokenizer

NLTK_VERSION = "3.9.4"
_data_dir: Path | None = None


def configure(data_dir: Path) -> None:
    """Point the tokenizers at a verified ``<data_dir>/tokenizers/punkt_tab`` tree."""
    global _data_dir
    _data_dir = Path(data_dir)
    _punkt.cache_clear()


@functools.lru_cache
def _punkt(language: str) -> PunktTokenizer:
    if _data_dir is None:
        raise RuntimeError("vendor_nltk.configure(data_dir) must be called first")
    return PunktTokenizer(_data_dir / "tokenizers" / "punkt_tab" / language)


def sent_tokenize(text: str, language: str = "english") -> list[str]:
    """Same as ``nltk.tokenize.sent_tokenize`` in nltk 3.9.4."""
    return _punkt(language).tokenize(text)


_treebank_word_tokenizer = NLTKWordTokenizer()


def word_tokenize(text: str, language: str = "english", preserve_line: bool = False) -> list[str]:
    """Same as ``nltk.tokenize.word_tokenize`` in nltk 3.9.4."""
    sentences = [text] if preserve_line else sent_tokenize(text, language)
    return [token for sent in sentences for token in _treebank_word_tokenizer.tokenize(sent)]
