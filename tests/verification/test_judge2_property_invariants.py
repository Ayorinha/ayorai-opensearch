from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from ayorai_attractor.verification.judge2 import adjudicate
from ayorai_attractor.verification.models import Evidence


def _evidence(item_id: str, *, excerpt: str = "claim") -> Evidence:
    return Evidence(
        id=item_id,
        claim_id="c1",
        source_id=f"source-{item_id}",
        source_location=f"https://example.test/{item_id}",
        retrieved_at=datetime(2026, 11, 4, tzinfo=UTC),
        start_offset=0,
        end_offset=len(excerpt),
        excerpt=excerpt,
        origin_id=f"origin-{item_id}",
    )


def _request(
    evidence_order: tuple[int, ...] = (0, 1, 2),
    stance_order: tuple[int, ...] = (0, 1, 2),
) -> dict[str, object]:
    items = [
        _evidence("e1"),
        _evidence("e2"),
        _evidence("e3"),
    ]
    relations = [
        {"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"},
        {"id": "st2", "atom_id": "a1", "evidence_id": "e2", "stance": "SUPPORTS"},
        {"id": "st3", "atom_id": "a1", "evidence_id": "e3", "stance": "CONTRADICTS"},
    ]
    return {
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": "claim",
        "atoms": [{"id": "a1", "text": "claim", "start_offset": 0, "end_offset": 5}],
        "evidence": [items[index] for index in evidence_order],
        "stances": [relations[index] for index in stance_order],
        "source_texts": {f"source-e{index + 1}": "claim" for index in range(3)},
    }


@given(
    evidence_order=st.permutations((0, 1, 2)),
    stance_order=st.permutations((0, 1, 2)),
)
def test_judge2_output_sha256_is_deterministic_and_order_invariant(
    evidence_order: tuple[int, ...],
    stance_order: tuple[int, ...],
) -> None:
    request = _request(evidence_order, stance_order)
    first = adjudicate(request)
    repeated = adjudicate(request)
    canonical_order = adjudicate(_request())

    assert first.output_sha256 == repeated.output_sha256
    assert first.output_sha256 == canonical_order.output_sha256
    assert first.to_dict()["output_sha256"] == first.output_sha256


@given(mode=st.sampled_from(("empty", "rejected")))
def test_judge2_without_admitted_evidence_never_returns_supported(mode: str) -> None:
    if mode == "empty":
        evidence: list[Evidence] = []
        source_texts: dict[str, str] = {}
        stances: list[dict[str, str]] = []
    else:
        evidence = [_evidence("e1", excerpt="fabricated")]
        source_texts = {"source-e1": "claim"}
        stances = [{"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}]

    result = adjudicate(
        {
            "protocol_version": "r2-a",
            "claim_id": "c1",
            "claim_text": "claim",
            "atoms": [{"id": "a1", "text": "claim", "start_offset": 0, "end_offset": 5}],
            "evidence": evidence,
            "stances": stances,
            "source_texts": source_texts,
        }
    )

    assert result.verdict != "SUPPORTED"
    assert result.decision_state in {"DECIDED", "ABSTAINED", "INVALID_INPUT"}
