from __future__ import annotations

import unicodedata
from itertools import pairwise

from .models import Evidence


def _nfc_with_map(text: str) -> tuple[str, list[int]]:
    """NFC-normalize text and map each normalized index to an original offset."""
    starts = [i for i, ch in enumerate(text) if unicodedata.combining(ch) == 0] or [0]
    if starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(text))
    parts: list[str] = []
    index_map: list[int] = []
    for begin, end in pairwise(starts):
        chunk = unicodedata.normalize("NFC", text[begin:end])
        parts.append(chunk)
        index_map.extend([begin] * len(chunk))
    index_map.append(len(text))
    return "".join(parts), index_map


NormalizedSource = tuple[str, list[int]]


def normalize_source(source_text: str) -> NormalizedSource:
    """Precompute the NFC text and offset map of a source for repeated lookups."""
    return _nfc_with_map(source_text)


class SourceText(str):
    """A source string that computes its NFC map once, on first lookup.

    It is an ordinary ``str`` everywhere else, so callers can pass it where a
    source text is expected without changing any signature. The map lives
    only as long as the object (one request in ``check_documents``).
    """

    __slots__ = ("_normalized",)
    _normalized: NormalizedSource | None

    def __new__(cls, value: str) -> SourceText:
        instance = super().__new__(cls, value)
        instance._normalized = None
        return instance

    def normalized(self) -> NormalizedSource:
        if self._normalized is None:
            self._normalized = _nfc_with_map(str(self))
        return self._normalized


def locate_excerpt(
    source_text: str, excerpt: str, normalized_source: NormalizedSource | None = None
) -> tuple[int, int] | None:
    """Return offsets of excerpt in the ORIGINAL source_text, or None.

    ``normalized_source`` must be ``normalize_source(source_text)``; passing it
    avoids renormalizing a large source for every excerpt.
    """
    target = unicodedata.normalize("NFC", excerpt)
    if not source_text or not target:
        return None
    if normalized_source is None:
        normalized_source = (
            source_text.normalized()
            if isinstance(source_text, SourceText)
            else _nfc_with_map(source_text)
        )
    normalized, index_map = normalized_source
    start = normalized.find(target)
    if start < 0:
        return None
    end = start + len(target)
    return index_map[start], index_map[end]


def revalidate_evidence(
    evidence: Evidence, source_text: str, normalized_source: NormalizedSource | None = None
) -> Evidence | None:
    located = locate_excerpt(source_text, evidence.excerpt, normalized_source)
    if located is None:
        return None
    start, end = located
    return evidence.model_copy(update={"start_offset": start, "end_offset": end})
