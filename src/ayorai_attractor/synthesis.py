"""Grounding gate for R6 synthesis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundingResult:
    grounded: bool
    unsupported_claims: tuple[str, ...]


def validate_claim_citations(
    claims: list[str],
    citation_ids_by_claim: dict[str, list[str]],
    available_evidence_ids: set[str],
) -> GroundingResult:
    """Require at least one known evidence id for every generated claim."""
    unsupported: list[str] = []
    for claim in claims:
        citations = citation_ids_by_claim.get(claim, [])
        if not citations or any(item not in available_evidence_ids for item in citations):
            unsupported.append(claim)
    return GroundingResult(not unsupported, tuple(unsupported))
