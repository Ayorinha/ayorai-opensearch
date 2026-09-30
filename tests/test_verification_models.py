from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ayorai_attractor.verification.models import (
    INSUFFICIENT_EVIDENCE_TO_VERDICT,
    Claim,
    Evidence,
    Stance,
    StanceEdge,
    Verdict,
)


def evidence(**overrides: object) -> Evidence:
    values: dict[str, object] = {
        "id": "e1",
        "claim_id": "c1",
        "source_id": "source-1",
        "source_location": "https://example.test/doc/1",
        "retrieved_at": datetime(2026, 9, 30, tzinfo=timezone.utc),
        "start_offset": 0,
        "end_offset": 12,
        "excerpt": "The claim is supported.",
        "origin_id": "origin-1",
    }
    values.update(overrides)
    return Evidence.model_validate(values)


def test_claim_is_strict_and_forbids_extra_fields() -> None:
    claim = Claim(id="c1", text="A factual claim.")
    assert claim.id == "c1"
    with pytest.raises(ValidationError):
        Claim(id="c1", text="A factual claim.", extra_field="nope")  # type: ignore[call-arg]


def test_evidence_requires_complete_provenance_shape() -> None:
    item = evidence()
    assert item.origin_id == "origin-1"
    assert item.canonical_url is None
    with pytest.raises(ValidationError):
        evidence(origin_id=None, canonical_url=None)


def test_evidence_rejects_invalid_offsets() -> None:
    with pytest.raises(ValidationError):
        evidence(start_offset=12, end_offset=12)


def test_stance_edge_is_explicit() -> None:
    edge = StanceEdge(id="edge-1", claim_id="c1", evidence_id="e1", stance=Stance.SUPPORTS)
    assert edge.stance is Stance.SUPPORTS


def test_verdict_has_exactly_six_r1_states() -> None:
    assert {item.value for item in Verdict} == {
        "verified", "supported", "partially_supported", "unverified", "refuted", "conflicting",
    }


def test_insufficient_evidence_maps_to_unverified_without_decision_logic() -> None:
    assert INSUFFICIENT_EVIDENCE_TO_VERDICT["insufficient_evidence"] is Verdict.UNVERIFIED
