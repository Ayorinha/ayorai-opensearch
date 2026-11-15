"""End-to-end scenarios through the HTTP API that the per-module tests do not cover.

Each test drives the real application (validation, passage selection, stance
detection, conservative filter, ADR-002 Judge) and pins the observed outcome.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api.app import app

CLAIM = "A receita da Vértice foi de 40 milhões em 2024."


def _check(*documents: str) -> dict[str, object]:
    response = TestClient(app).post(
        "/v1/check",
        json={
            "claims": [CLAIM],
            "documents": [{"id": f"d{i}", "text": text} for i, text in enumerate(documents)],
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert isinstance(result, dict)
    return result


def test_independent_documents_that_disagree_are_conflicting() -> None:
    result = _check(CLAIM, "A receita da Vértice foi de 55 milhões em 2024.")
    assert result["status"] == "conflicting"
    assert result["verdict"] == "conflicting"


def test_numeric_divergence_is_refuted_with_the_divergent_excerpt() -> None:
    document = "A receita da Vértice foi de 55 milhões em 2024."
    result = _check(document)
    assert result["verdict"] == "refuted"
    evidence = result["evidence"]
    assert isinstance(evidence, list) and evidence
    assert evidence[0]["excerpt"] == document
    assert (evidence[0]["start"], evidence[0]["end"]) == (0, len(document))


def test_claim_and_document_in_different_languages_abstain() -> None:
    """Known limitation: the conservative filter needs literal word overlap.

    A Portuguese claim checked against an English document that states the same
    fact is never supported; the system abstains instead of deciding.
    """
    result = _check("Vertice reported revenue of 40 million in 2024.")
    assert result["status"] == "abstain/no_answer"
    assert result["verdict"] is None
    assert result["abstention_reason"] == "insufficient_evidence"


def test_audit_persistence_failure_returns_a_server_error_not_a_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_record(*_args: object, **_kwargs: object) -> str:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(app_module.audit_store, "record", failing_record)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/audit", json={"query": "falha de persistência simulada"}
    )
    assert response.status_code == 500
    assert "trace_id" not in response.text
    assert "disk I/O error" not in response.text
