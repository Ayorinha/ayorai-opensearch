from __future__ import annotations

import unicodedata

from .models import Evidence


def locate_excerpt(source_text: str, excerpt: str) -> tuple[int, int] | None:
    source = unicodedata.normalize("NFC", source_text)
    target = unicodedata.normalize("NFC", excerpt)
    if not source or not target:
        return None
    start = source.find(target)
    if start < 0:
        return None
    return start, start + len(target)


def revalidate_evidence(evidence: Evidence, source_text: str) -> Evidence | None:
    located = locate_excerpt(source_text, evidence.excerpt)
    if located is None:
        return None
    start, end = located
    return evidence.model_copy(update={"start_offset": start, "end_offset": end})
