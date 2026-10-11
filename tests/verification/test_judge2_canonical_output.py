from __future__ import annotations

import socket
from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.judge2 import adjudicate
from ayorai_attractor.verification.models import Evidence


def evidence(item_id: str = "e1", *, claim_id: str = "c1") -> Evidence:
    return Evidence(
        id=item_id,
        claim_id=claim_id,
        source_id=f"source-{item_id}",
        source_location=f"https://example.test/{item_id}",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        start_offset=0,
        end_offset=1,
        excerpt="x",
        origin_id=f"origin-{item_id}",
    )


def request_one(*, out_of_scope: bool = False, invalid: bool = False) -> dict[str, object]:
    claim_text = "Claim A"
    atoms: list[dict[str, object]] = [] if invalid else [
        {"id": "a1", "text": claim_text, "start_offset": 0, "end_offset": len(claim_text)}
    ]
    return {
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": claim_text,
        "atoms": atoms,
        "evidence": [] if invalid or out_of_scope else [evidence()],
        "stances": [] if invalid or out_of_scope else [
            {"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}
        ],
        "source_texts": {} if invalid or out_of_scope else {"source-e1": "x"},
        "out_of_scope": out_of_scope,
    }


def test_t7_canonical_bytes_are_identical_for_repeated_and_reordered_inputs() -> None:
    claim_text = "Alpha Beta"
    request: dict[str, object] = {
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": claim_text,
        "atoms": [
            {"id": "a1", "text": "Alpha", "start_offset": 0, "end_offset": 5},
            {"id": "a2", "text": "Beta", "start_offset": 6, "end_offset": 10},
        ],
        "evidence": [evidence("e1"), evidence("e2")],
        "stances": [
            {"id": "st1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"},
            {"id": "st2", "atom_id": "a2", "evidence_id": "e2", "stance": "CONTRADICTS"},
        ],
        "source_texts": {"source-e1": "x", "source-e2": "x"},
    }
    shuffled = {
        **request,
        "atoms": list(reversed(request["atoms"])),  # type: ignore[arg-type]
        "evidence": list(reversed(request["evidence"])),  # type: ignore[arg-type]
        "stances": list(reversed(request["stances"])),  # type: ignore[arg-type]
    }

    first = adjudicate(request).canonical_bytes()
    assert first == adjudicate(request).canonical_bytes()
    assert first == adjudicate(shuffled).canonical_bytes()


@pytest.mark.parametrize(
    ("input_case", "expected_state"),
    [
        (request_one(), "DECIDED"),
        (request_one(out_of_scope=True), "ABSTAINED"),
        (request_one(invalid=True), "INVALID_INPUT"),
    ],
)
def test_t8_invariant_i1_holds_for_every_decision_state(
    input_case: dict[str, object], expected_state: str
) -> None:
    result = adjudicate(input_case)
    assert result.decision_state == expected_state
    assert (result.verdict is not None) is (result.decision_state == "DECIDED")
    assert result.to_dict()["output_sha256"] == result.output_sha256
    assert result.output_sha256 == __import__("hashlib").sha256(
        __import__("ayorai_attractor.verification.judge2", fromlist=["canonical_json_bytes"])
        .canonical_json_bytes({
            key: value for key, value in result.to_dict().items() if key != "output_sha256"
        })
    ).hexdigest()


def test_t9_adjudication_executes_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted during Judge 2.0 adjudication")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    result = adjudicate(request_one())
    assert result.decision_state == "DECIDED"
    assert result.verdict == "SUPPORTED"


def test_three_fixed_output_sha256_vectors() -> None:
    vectors = [
        (
            request_one(),
            "0000000000000000000000000000000000000000000000000000000000000000",
        ),
        (
            request_one(out_of_scope=True),
            "0000000000000000000000000000000000000000000000000000000000000000",
        ),
        (
            request_one(invalid=True),
            "0000000000000000000000000000000000000000000000000000000000000000",
        ),
    ]
    actual = [adjudicate(request).output_sha256 for request, _ in vectors]
    expected = [digest for _, digest in vectors]
    assert actual == expected
