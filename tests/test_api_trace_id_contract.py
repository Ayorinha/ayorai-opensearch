"""Contract of the trace identifiers returned by each route.

Only /v1/audit persists its trace; GET /v1/audit/{trace_id} answers 404 for every
other identifier, including the "tr_" identifier of /v1/opensearch, which has the
same prefix. "chk_" and "fld_" identifiers are content digests: the same request
gives the same identifier and result, so a result is reproduced by resending the
request, not retrieved. /v1/verify returns no trace identifier.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.audit_store import AuditTraceStore

TEXT = "A receita da Vértice foi de 40 milhões em 2024."
CHECK = {"claims": [TEXT], "documents": [{"id": "d", "text": TEXT}]}
FIELDS = {
    "document": {"id": "d", "text": TEXT},
    "fields": [{"name": "receita", "type": "number", "value": "40"}],
}
SEARCH = {"query": "receita da Vértice em 2024"}


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> TestClient:
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"))
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    return TestClient(app_module.app)


def _trace(client: TestClient, path: str, body: dict[str, Any]) -> str:
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    trace_id = response.json()["trace_id"]
    assert isinstance(trace_id, str)
    return trace_id


@pytest.mark.parametrize(
    ("path", "body", "prefix"),
    [("/v1/check", CHECK, "chk_"), ("/v1/fields", FIELDS, "fld_")],
)
def test_content_digest_traces_are_reproducible_and_not_persisted(
    client: TestClient, path: str, body: dict[str, Any], prefix: str
) -> None:
    first = client.post(path, json=body)
    second = client.post(path, json=body)
    assert first.status_code == second.status_code == 200
    trace_id = first.json()["trace_id"]
    assert re.fullmatch(prefix + "[0-9a-f]{32}", trace_id)
    assert second.json() == first.json()
    assert client.get(f"/v1/audit/{trace_id}").status_code == 404


def test_opensearch_trace_has_the_audit_prefix_but_is_not_persisted(client: TestClient) -> None:
    first = _trace(client, "/v1/opensearch", SEARCH)
    second = _trace(client, "/v1/opensearch", SEARCH)
    assert first.startswith("tr_") and second.startswith("tr_")
    assert first != second  # a new identifier per execution, not a digest
    assert client.get(f"/v1/audit/{first}").status_code == 404


def test_audit_trace_is_persisted_and_retrievable(client: TestClient) -> None:
    first = _trace(client, "/v1/audit", SEARCH)
    second = _trace(client, "/v1/audit", SEARCH)
    assert first.startswith("tr_") and first != second
    for trace_id in (first, second):
        stored = client.get(f"/v1/audit/{trace_id}")
        assert stored.status_code == 200
        body = stored.json()
        assert body["trace_id"] == trace_id
        assert body["verdict_authority"] == "not_adjudicated"
        assert body["replay_integrity"] == "valid"


def test_verify_returns_no_trace_identifier(client: TestClient) -> None:
    response = client.post(
        "/v1/verify",
        json={"claims": [{"id": "c1", "text": TEXT}], "evidence": [], "stances": []},
    )
    assert response.status_code == 200
    assert "trace_id" not in response.json()
