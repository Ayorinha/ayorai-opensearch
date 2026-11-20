"""The /v2/audit trace attests the adjudication actually returned (r2-v4).

Regression: the trace was recorded before adjudication and held only retrieval
counts, so it could not show which verdicts a client received.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
import rfc8785
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import QualityMode, SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse
from ayorai_attractor.verification.check_models import (
    ADJUDICATION_DIGEST_FIELDS,
    adjudication_sha256,
)

KEY = ("k1", b"\x07" * 32)
FACT = "A receita da Vértice foi de 40 milhões em 2024."
QUERY = "Qual foi a receita da Vértice em 2024?"


class _Search(Provider):
    id = "fake-search"

    def execute(self, prompt: str) -> ProviderResponse:
        text = "Segundo o balanço, a receita da Vértice foi de 40 milhões em 2024."
        return ProviderResponse(
            text=text, source="https://example.test/b", excerpt=text, independent=True
        )


@pytest.fixture
def store(tmp_path: Path, request: pytest.FixtureRequest) -> AuditTraceStore:
    trace_store = AuditTraceStore(str(tmp_path / "audit.sqlite3"), mac_keys=(KEY,))
    request.addfinalizer(trace_store.close)
    return trace_store


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, store: AuditTraceStore) -> TestClient:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=_Search()))
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    return TestClient(app_module.app)


def _audit(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/v2/audit", json=body)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()
    return data


def _client_side_digest(body: dict[str, Any]) -> str:
    """What a client computes from the body it received (independent of the server code)."""
    covered = {name: body[name] for name in ADJUDICATION_DIGEST_FIELDS}
    return hashlib.sha256(rfc8785.dumps(covered)).hexdigest()


def _db(store: AuditTraceStore) -> sqlite3.Connection:
    return sqlite3.connect(store.path)


def test_trace_binds_the_returned_adjudication(client: TestClient) -> None:
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    assert body["results"][0]["verdict"] == "partially_supported"
    assert body["adjudication_sha256"] == _client_side_digest(body)
    trace = client.get(f"/v1/audit/{body['trace_id']}").json()
    assert trace["replay_version"] == "r2-v4"
    assert trace["replay_integrity"] == "valid"
    assert trace["adjudication_sha256"] == body["adjudication_sha256"]
    assert trace["check_trace_id"] == body["check_trace_id"] is not None


def test_a_changed_verdict_no_longer_matches_the_trace(client: TestClient) -> None:
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    altered = {**body, "results": [{**body["results"][0], "verdict": "verified"}]}
    assert _client_side_digest(altered) != body["adjudication_sha256"]


def test_abstention_without_sources_is_also_bound(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=None))
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    assert body["check_trace_id"] is None
    assert body["results"][0]["abstention_reason"] == "no_independent_source"
    trace = client.get(f"/v1/audit/{body['trace_id']}").json()
    assert (trace["replay_version"], trace["replay_integrity"]) == ("r2-v4", "valid")
    assert trace["check_trace_id"] is None
    assert trace["adjudication_sha256"] == _client_side_digest(body)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("adjudication_sha256", "f" * 64),
        ("check_trace_id", "chk_forged"),
        ("adjudication_sha256", None),
    ],
)
def test_tampering_with_the_bound_adjudication_is_detected(
    client: TestClient, store: AuditTraceStore, column: str, value: str | None
) -> None:
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    with closing(_db(store)) as connection, connection:
        connection.execute(
            f"UPDATE audit_traces SET {column} = ? WHERE trace_id = ?",  # noqa: S608
            (value, body["trace_id"]),
        )
    assert store.verify(body["trace_id"]) == "invalid"


def test_downgrading_r2_v4_to_r2_v3_is_detected(client: TestClient, store: AuditTraceStore) -> None:
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    with closing(_db(store)) as connection, connection:
        connection.execute(
            "UPDATE audit_traces SET replay_version = 'r2-v3', check_trace_id = NULL, "
            "adjudication_sha256 = NULL WHERE trace_id = ?",
            (body["trace_id"],),
        )
    assert store.verify(body["trace_id"]) == "invalid"


def test_an_adjudication_attached_to_an_older_trace_is_rejected(
    client: TestClient, store: AuditTraceStore
) -> None:
    response = client.post("/v1/audit", json={"query": QUERY})
    assert response.status_code == 200, response.text
    trace_id = response.json()["trace_id"]
    trace = client.get(f"/v1/audit/{trace_id}").json()
    assert (trace["replay_version"], trace["adjudication_sha256"]) == ("r2-v3", None)
    assert trace["replay_integrity"] == "valid"
    with closing(_db(store)) as connection, connection:
        connection.execute(
            "UPDATE audit_traces SET adjudication_sha256 = ? WHERE trace_id = ?",
            ("a" * 64, trace_id),
        )
    assert store.verify(trace_id) == "invalid"


def test_removing_the_mac_of_an_r2_v4_trace_is_detected(
    client: TestClient, store: AuditTraceStore
) -> None:
    body = _audit(client, {"query": QUERY, "claims": [FACT]})
    with closing(_db(store)) as connection, connection:
        connection.execute(
            "UPDATE audit_traces SET replay_mac = NULL WHERE trace_id = ?", (body["trace_id"],)
        )
    assert store.verify(body["trace_id"]) == "invalid"


def test_unsealed_r2_v4_traces_are_sealed(tmp_path: Path) -> None:
    path = str(tmp_path / "s.sqlite3")
    response = Attractor().run(SearchRequest(query=QUERY, mode=list(QualityMode)[0]))
    report = AuditReport.from_response(response)
    with AuditTraceStore(path, mac_keys=()) as plain:
        plain.record(response, report, adjudication=(None, "b" * 64))
        assert plain.verify(report.trace_id) == "valid"
    with AuditTraceStore(path, mac_keys=(KEY,)) as keyed:
        assert keyed.verify(report.trace_id) == "invalid"  # unsealed under keys
        assert keyed.seal_unsealed() == 1
        assert keyed.verify(report.trace_id) == "valid"


@pytest.mark.parametrize("bad", ["", "B" * 64, "a" * 63, "z" * 64])
def test_record_rejects_a_malformed_adjudication_digest(store: AuditTraceStore, bad: str) -> None:
    response = Attractor().run(SearchRequest(query=QUERY, mode=list(QualityMode)[0]))
    with pytest.raises(ValueError, match="adjudication_sha256"):
        store.record(response, AuditReport.from_response(response), adjudication=(None, bad))


def test_server_helper_matches_the_documented_client_computation() -> None:
    body = {
        "check_trace_id": "chk_x",
        "claims_source": "caller_claims",
        "engine": {"judge": "ADR-002"},
        "documents": [],
        "results": [{"claim": "Ação ç", "confidence": 0.5}],
        "summary": {"ignored": 1},
    }
    assert adjudication_sha256(body) == _client_side_digest(body)
