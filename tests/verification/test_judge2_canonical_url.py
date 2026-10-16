"""Regression tests for issue #182: evidence[].canonical_url on the r2-a path."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.judge2.adjudication import verify_output


def r2_a_request() -> dict[str, object]:
    """Minimal valid r2-a request (same shape as tests/test_verification_api.py)."""
    return {
        "schema_version": "r2-a",
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": "Claim A",
        "atoms": [{"id": "a1", "text": "Claim A", "start_offset": 0, "end_offset": 7}],
        "evidence": [
            {
                "id": "e1",
                "claim_id": "c1",
                "source_id": "source-e1",
                "source_location": "document:1",
                "retrieved_at": "2026-10-11T12:00:00Z",
                "start_offset": 0,
                "end_offset": 7,
                "excerpt": "Claim A",
                "origin_id": "origin-e1",
            }
        ],
        "stances": [{"id": "s1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}],
        "source_texts": {"source-e1": "Claim A"},
    }


def _with_urls(*urls: str) -> dict[str, object]:
    request = r2_a_request()
    base_evidence = request["evidence"][0]  # type: ignore[index]
    evidence = []
    stances = []
    for index, url in enumerate(urls, start=1):
        item = dict(  # type: ignore[call-overload]
            base_evidence, id=f"e{index}", source_id=f"source-e{index}", canonical_url=url
        )
        item.pop("origin_id")
        request["source_texts"][f"source-e{index}"] = "Claim A"  # type: ignore[index]
        evidence.append(item)
        stances.append(
            {"id": f"s{index}", "atom_id": "a1", "evidence_id": f"e{index}", "stance": "SUPPORTS"}
        )
    request["evidence"] = evidence
    request["stances"] = stances
    return request


def _post(request: dict[str, object]) -> dict[str, object]:
    response = TestClient(app).post("/v1/verify", json=request)
    assert response.status_code == 200, response.text
    return response.json()["result"]  # type: ignore[no-any-return]


def test_canonical_url_is_adjudicated_not_rejected() -> None:
    result = _post(_with_urls("https://example.test/a"))
    assert result["decision_state"] == "DECIDED"
    assert result["verdict"] == "SUPPORTED"
    assert "SCHEMA_VIOLATION" not in result["reason_codes"]


def test_canonical_url_result_is_deterministic_and_verifiable() -> None:
    first = _post(_with_urls("https://example.test/a"))
    second = _post(_with_urls("https://example.test/a"))
    assert first["input_sha256"] == second["input_sha256"]
    assert first["output_sha256"] == second["output_sha256"]
    assert verify_output(first)


def test_canonical_url_hash_uses_normalized_form() -> None:
    bare = _post(_with_urls("https://example.test"))
    slash = _post(_with_urls("https://example.test/"))
    assert bare["input_sha256"] == slash["input_sha256"]


def test_different_canonical_url_changes_input_hash() -> None:
    a = _post(_with_urls("https://example.test/a"))
    b = _post(_with_urls("https://example.test/b"))
    assert a["input_sha256"] != b["input_sha256"]


def test_same_canonical_url_counts_as_one_source() -> None:
    same = _post(_with_urls("https://example.test/a", "https://example.test/a"))
    distinct = _post(_with_urls("https://example.test/a", "https://example.org/b"))
    assert same["verdict"] == distinct["verdict"] == "SUPPORTED"
    assert same["robustness"] == "R1"
    assert distinct["robustness"] != "R1"


def test_invalid_canonical_url_is_rejected_by_the_api() -> None:
    response = TestClient(app).post("/v1/verify", json=_with_urls("not-a-url"))
    assert response.status_code == 422


def test_json_safe_converts_only_validated_urls() -> None:
    from decimal import Decimal

    from pydantic import HttpUrl

    from ayorai_attractor.verification.judge2.adjudication import _json_safe

    assert _json_safe(HttpUrl("https://example.test/a")) == "https://example.test/a"
    assert _json_safe(HttpUrl("https://example.test")) == "https://example.test/"
    with pytest.raises(TypeError):
        _json_safe(Decimal("1.5"))
