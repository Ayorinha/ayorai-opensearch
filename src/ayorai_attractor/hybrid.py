"""Deterministic hybrid retrieval rank fusion for R5."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RankedHit:
    document_id: str
    score: float


def rrf_fuse(
    lexical: list[RankedHit],
    semantic: list[RankedHit],
    *,
    k: int = 60,
    lexical_weight: float = 0.5,
    semantic_weight: float = 0.5,
) -> list[RankedHit]:
    """Fuse two ranked lists using weighted reciprocal rank fusion."""
    if k <= 0:
        raise ValueError("k must be positive")
    if lexical_weight < 0 or semantic_weight < 0:
        raise ValueError("weights must be non-negative")
    if lexical_weight + semantic_weight == 0:
        raise ValueError("at least one retrieval weight must be positive")

    totals: dict[str, float] = {}
    for weight, ranking in ((lexical_weight, lexical), (semantic_weight, semantic)):
        for rank, hit in enumerate(ranking, start=1):
            totals[hit.document_id] = totals.get(hit.document_id, 0.0) + (
                weight / (k + rank)
            )

    return [
        RankedHit(document_id=document_id, score=score)
        for document_id, score in sorted(
            totals.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
