from __future__ import annotations


import pytest



SOURCE = "The regulator published Resolution 765 in 2023."
CLAIM = "Resolution 765 was published in 2023."
ATOM = {"id": "a1", "text": CLAIM, "start_offset": 0, "end_offset": len(CLAIM)}


def run_gates(**kwargs: object) -> object:
    from ayorai_attractor.verification.judge2 import evaluate_gates

    return evaluate_gates(**kwargs)


def evidence(
    *,
    item_id: str = "e1",
    source_text: str = SOURCE,
    start: int = 0,
    end: int = 10,
    normalized_hash: str | None = None,
) -> object:
    from datetime import UTC, datetime
    from ayorai_attractor.verification.models import Evidence

    return Evidence(
        id=item_id,
        claim_id="c1",
        source_id="s1",
        source_location="https://example.test/source",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        start_offset=start,
        end_offset=end,
        excerpt=source_text[start:end] or "x",
        origin_id="origin-1",
        normalized_content_hash=normalized_hash,
    )


def valid_kwargs() -> dict[str, object]:
    return {
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": CLAIM,
        "atoms": [ATOM],
        "evidence": [evidence()],
        "stances": [{"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}],
        "source_texts": {"s1": SOURCE},
    }


def test_contract_digest_is_pinned_to_approved_judge_2_contract() -> None:
    from ayorai_attractor.verification.judge2 import RULES_SHA256, rules_sha256

    assert rules_sha256() == RULES_SHA256
    assert RULES_SHA256 == (
        "7bf2fd141bcc7cdd370364d3a162dfcdc4ea45e88182d27c4f3583b08616574e"
    )


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"protocol_version": "r99-a"}, "UNSUPPORTED_PROTOCOL_VERSION"),
        ({"claim_text": "   "}, "EMPTY_CLAIM"),
        ({"atoms": []}, "NO_ATOMS"),
        ({"atoms": [ATOM, dict(ATOM)]}, "DUPLICATE_ID"),
        (
            {"stances": [{
                "id": "st1", "atom_id": "missing", "evidence_id": "e1",
                "stance": "SUPPORTS",
            }]},
            "DANGLING_REFERENCE",
        ),
        ({"stances": [
            {"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"},
            {"id": "st2", "atom_id": "a1", "evidence_id": "e1", "stance": "CONTRADICTS"},
        ]}, "DUPLICATE_STANCE"),
        (
            {"atoms": [{
                "id": "a1", "text": CLAIM, "start_offset": 0,
                "end_offset": len(CLAIM) + 1,
            }]},
            "ATOM_SPAN_OUT_OF_RANGE",
        ),
        ({"atoms": ["not-an-atom"]}, "SCHEMA_VIOLATION"),
    ],
)
def test_t11_each_g1_code_has_a_specific_negative_case(
    override: dict[str, object], code: str
) -> None:
    kwargs = valid_kwargs()
    kwargs.update(override)
    result = run_gates(**kwargs)
    assert result.decision_state == "INVALID_INPUT"
    assert result.reason_codes == (code,)
    assert result.admissible is False
    assert not hasattr(result, "verdict")


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"out_of_scope": True}, "OUT_OF_SCOPE"),
        ({"factual_claim": False}, "NON_FACTUAL_CLAIM"),
        ({"temporal_anchor_present": False}, "MISSING_TEMPORAL_ANCHOR"),
        ({"retrieval_succeeded": False}, "RETRIEVAL_FAILURE"),
        ({"evidence_pool_integrity_ok": False}, "EVIDENCE_POOL_INTEGRITY_FAILURE"),
    ],
)
def test_g2_returns_abstention_reason_without_verdict(
    override: dict[str, Any], code: str
) -> None:
    kwargs = valid_kwargs()
    kwargs.update(override)
    result = run_gates(**kwargs)
    assert result.decision_state == "ABSTAINED"
    assert code in result.reason_codes
    assert result.admissible is False
    assert not hasattr(result, "verdict")


@pytest.mark.parametrize(
    ("kwargs_update", "expected_reason"),
    [
        ({"source_texts": {}}, "OFFSET_INVALID"),
        ({"evidence": [evidence(normalized_hash="0" * 64)]}, "EXCERPT_MISMATCH"),
        (
            {"stances": [{
                "id": "st1", "atom_id": "a1", "evidence_id": "e1",
                "stance": "NEUTRAL",
            }]},
            "NEUTRAL_STANCE",
        ),
    ],
)
def test_t11_each_evidence_rejection_reason_is_recorded(
    kwargs_update: dict[str, Any], expected_reason: str
) -> None:
    kwargs = valid_kwargs()
    kwargs.update(kwargs_update)
    result = run_gates(**kwargs)
    assert result.decision_state is None
    assert result.admissible is True
    assert len(result.evidence) == 1
    assert result.evidence[0].admitted is False
    assert result.evidence[0].reason == expected_reason
    assert not hasattr(result, "verdict")


def test_valid_supporting_evidence_is_admitted_without_verdict() -> None:
    result = evaluate_gates(**valid_kwargs())
    assert result.decision_state is None
    assert result.reason_codes == ()
    assert result.admissible is True
    assert result.evidence[0].admitted is True
    assert result.evidence[0].reason is None
    assert not hasattr(result, "verdict")


def test_multiple_g2_reasons_are_preserved_in_normative_order() -> None:
    kwargs = valid_kwargs()
    kwargs.update(out_of_scope=True, factual_claim=False, retrieval_succeeded=False)
    result = run_gates(**kwargs)
    assert result.decision_state == "ABSTAINED"
    assert result.reason_codes == (
        "OUT_OF_SCOPE",
        "NON_FACTUAL_CLAIM",
        "RETRIEVAL_FAILURE",
    )


