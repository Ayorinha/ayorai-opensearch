"""Provenance: client-supplied text never reaches "verified" (ADR-002 §2).

Regression: every document of /v1/check was marked with complete provenance, so two
pasted texts without any verified origin made a claim "verified". "verified" requires
an origin this server retrieved itself, at a known time, with a stable URL.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.verification.document_check import CheckDocumentInput, check_documents

CLAIM = "A receita da Vértice foi de 40 milhões de reais em 2024."
A = "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024."
B = "Em 2024, a Vértice teve receita de 40 milhões de reais, informou a agência."


def _docs(**fields: Any) -> list[CheckDocumentInput]:
    return [
        CheckDocumentInput(id="a", text=A, **fields.get("a", {})),
        CheckDocumentInput(id="b", text=B, **fields.get("b", {})),
    ]


def test_client_supplied_documents_cap_at_supported_even_with_a_declared_url() -> None:
    docs = _docs(a={"url": "https://a.example/x"}, b={"url": "https://b.example/y"})
    result = check_documents(docs, claims=[CLAIM])
    assert result.results[0].verdict == "supported"
    assert [d["provenance"] for d in result.documents] == ["client_supplied"] * 2


def test_server_retrieved_documents_with_urls_can_be_verified() -> None:
    server = {"retrieved_by_server": True}
    docs = _docs(
        a={**server, "url": "https://a.example/x"}, b={**server, "url": "https://b.example/y"}
    )
    result = check_documents(docs, claims=[CLAIM])
    assert result.results[0].verdict == "verified"
    assert [d["provenance"] for d in result.documents] == ["server_retrieved"] * 2


@pytest.mark.parametrize(
    "fields",
    [
        {"a": {"retrieved_by_server": True}, "b": {"retrieved_by_server": True}},
        {"a": {"retrieved_by_server": True, "url": "https://a.example/x"}, "b": {}},
    ],
)
def test_any_supporting_source_without_complete_provenance_caps_at_supported(
    fields: dict[str, dict[str, Any]],
) -> None:
    assert check_documents(_docs(**fields), claims=[CLAIM]).results[0].verdict == "supported"


def test_provenance_is_part_of_the_check_identity() -> None:
    client = check_documents(_docs(), claims=[CLAIM])
    server = check_documents(
        _docs(a={"retrieved_by_server": True}, b={"retrieved_by_server": True}), claims=[CLAIM]
    )
    assert client.trace_id != server.trace_id


def test_v1_check_reports_client_supplied_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    body = {
        "claims": [CLAIM],
        "documents": [
            {"id": "a", "text": A, "url": "https://a.example/x"},
            {"id": "b", "text": B, "url": "https://b.example/y"},
        ],
    }
    response = TestClient(app_module.app).post("/v1/check", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["results"][0]["verdict"] == "supported"
    assert {d["provenance"] for d in data["documents"]} == {"client_supplied"}


def test_v2_audit_marks_retrieved_sources_as_server_retrieved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, request: pytest.FixtureRequest
) -> None:
    from ayorai_attractor.audit_store import AuditTraceStore
    from ayorai_attractor.orchestrator import Attractor
    from ayorai_attractor.providers.base import Provider, ProviderResponse

    class _Search(Provider):
        id = "fake-search"

        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(
                text=A, source="https://example.test/balanco", excerpt=A, independent=True
            )

    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"), mac_keys=())
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=_Search()))
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    response = TestClient(app_module.app).post(
        "/v2/audit", json={"query": "receita da Vértice", "claims": [CLAIM]}
    )
    assert response.status_code == 200, response.text
    assert [d["provenance"] for d in response.json()["documents"]] == ["server_retrieved"]
