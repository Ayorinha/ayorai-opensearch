"""Decision errors of /v1/check found in review, pinned through the real HTTP application.

Each was first pinned as a strict ``xfail``. Detector v9 fixes the cross-sentence
token negation and the reported denial; detector v13 fixes the bare scale words.
They are now ordinary regression tests. The control tests pin behaviour
that was already correct, so a fix cannot break it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api.app import app
from ayorai_attractor.audit_store import AuditTraceStore

CLAIM = "A receita da Vértice foi de 40 milhões em 2024."
SUPPORTING = "Segundo o balanço, a receita da Vértice foi de 40 milhões em 2024."


def _check(claim: str, *documents: str) -> dict[str, object]:
    response = TestClient(app).post(
        "/v1/check",
        json={
            "claims": [claim],
            "documents": [{"id": f"d{i}", "text": text} for i, text in enumerate(documents)],
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert isinstance(result, dict)
    return result


def _stances(result: dict[str, object]) -> list[object]:
    evidence = result["evidence"]
    assert isinstance(evidence, list)
    return [item["stance"] for item in evidence]


def test_a_document_that_declares_the_claim_false_does_not_support_it() -> None:
    result = _check(CLAIM, "É falso que a receita da Vértice foi de 40 milhões em 2024.")
    assert _stances(result) == ["contradicts"]
    assert result["verdict"] == "refuted"


def test_a_denial_and_a_confirmation_are_conflicting_not_verified() -> None:
    result = _check(
        CLAIM, "É falso que a receita da Vértice foi de 40 milhões em 2024.", SUPPORTING
    )
    assert result["status"] == "conflicting"


def test_a_previous_year_value_does_not_support_a_claim_about_the_current_year() -> None:
    result = _check(
        "O número de reclamações foi 40 em 2024.",
        "O número de reclamações caiu para 31 em 2024, contra 40 no ano anterior.",
    )
    assert "supports" not in _stances(result)


def test_a_negation_in_another_sentence_does_not_refute_the_claim() -> None:
    result = _check(CLAIM, "A Vértice não faliu. A receita da Vértice foi de 40 milhões em 2024.")
    assert _stances(result) == ["supports"]


def test_a_document_saying_it_is_not_true_refutes_the_claim() -> None:
    """Control: token negation ('Não é verdade que') is already handled."""
    result = _check(CLAIM, "Não é verdade que a receita da Vértice foi de 40 milhões em 2024.")
    assert result["verdict"] == "refuted"


def test_two_confirming_documents_are_supported() -> None:
    """Control: a fix for negation must not weaken plain corroboration.

    The two documents must be independently worded: the same sentence with a prefix
    is one source under ADR-002 §3 (see test_document_check_source_independence.py).
    Client-supplied documents reach "supported", the strongest verdict available
    without server-verified provenance (ADR-002 §2).
    """
    independent = "Em 2024, a Vértice teve receita de 40 milhões, informou a agência."
    result = _check(CLAIM, SUPPORTING, independent)
    assert result["status"] == "supported"
    assert _stances(result) == ["supports", "supports"]


def test_check_trace_ids_are_not_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> None:
    """Current contract: /v1/check results are not stored in the audit store.

    The trace_id is a content digest; the result is reproduced by resending the
    same request, not retrieved from GET /v1/audit/{trace_id}.
    """
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    client = TestClient(app)
    body = {"claims": [CLAIM], "documents": [{"id": "d", "text": CLAIM}]}

    first = client.post("/v1/check", json=body)
    second = client.post("/v1/check", json=body)

    assert first.status_code == second.status_code == 200
    trace_id = first.json()["trace_id"]
    assert trace_id == second.json()["trace_id"]
    assert first.json()["results"] == second.json()["results"]
    assert client.get(f"/v1/audit/{trace_id}").status_code == 404


def test_equivalent_values_with_different_scale_words_are_not_refuted() -> None:
    result = _check(
        "A receita da Vértice foi de 1,2 bilhão em 2024.",
        "A receita da Vértice foi de 1.200 milhões em 2024.",
    )
    assert result["verdict"] != "refuted"


def test_a_reported_denial_does_not_support_the_claim() -> None:
    result = _check(CLAIM, "A Vértice negou que a receita da Vértice foi de 40 milhões em 2024.")
    assert "supports" not in _stances(result)
