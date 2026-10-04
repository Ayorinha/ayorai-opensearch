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


def locate_excerpt(source_text: str, excerpt: str) -> tuple[int, int] | None:
    """Return offsets of excerpt in the ORIGINAL source_text, or None."""
    target = unicodedata.normalize("NFC", excerpt)
    if not source_text or not target:
        return None
    normalized, index_map = _nfc_with_map(source_text)
    start = normalized.find(target)
    if start < 0:
        return None
    end = start + len(target)
    return index_map[start], index_map[end]


def revalidate_evidence(evidence: Evidence, source_text: str) -> Evidence | None:
    located = locate_excerpt(source_text, evidence.excerpt)
    if located is None:
        return None
    start, end = located
    return evidence.model_copy(update={"start_offset": start, "end_offset": end})
