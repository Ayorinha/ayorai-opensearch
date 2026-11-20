"""Each search hit is its own source, with its own provenance, end to end.

Regression: the OpenSearch providers concatenated every hit into one text cut at
2,000 characters, so /v2/audit saw one document: never more than one independent
source (verdict ceiling "partially_supported"), no per-hit URL or id, and content
after the cut was lost.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.opensearch import (
    MAX_SOURCE_CHARS,
    HybridOpenSearchProvider,
    OpenSearchProvider,
)

ENDPOINT = "https://search.example.test"
CLAIM = "A receita da Vértice foi de 40 milhões de reais em 2024."


def _hit(doc_id: str, content: str, **extra: Any) -> dict[str, Any]:
    return {"_id": doc_id, "_score": 1.0, "_source": {"title": "", "content": content, **extra}}


def _provider(*hits: dict[str, Any]) -> OpenSearchProvider:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"hits": {"hits": list(hits)}})
    )
    return OpenSearchProvider(ENDPOINT, "docs", transport=transport)


def test_each_hit_becomes_a_source_with_its_own_provenance() -> None:
    response = _provider(
        _hit("a", "Primeiro.", url="https://a.example/x", published_at="2025-02-01"),
        _hit("b", "Segundo."),
        _hit("c", "Terceiro.", url="ftp://not-allowed/x"),
        _hit("d", "   "),
    ).execute("consulta")
    first, second, third = response.documents
    assert (first.source, first.url, first.source_id, first.published_at) == (
        "https://a.example/x",
        "https://a.example/x",
        "a",
        "2025-02-01",
    )
    assert (second.source, second.url) == (f"{ENDPOINT}/docs/_doc/b", None)
    assert third.url is None  # only http(s) URLs are taken as canonical
    assert response.text.startswith("Primeiro.")  # the combined text is unchanged


def test_long_content_is_kept_per_document_up_to_the_cap() -> None:
    long = "x " * 1500 + "A receita foi de 40 milhões."
    (source,) = _provider(_hit("a", long)).execute("q").documents
    assert source.content.endswith("40 milhões.")
    (capped,) = _provider(_hit("a", "y" * (MAX_SOURCE_CHARS + 50))).execute("q").documents
    assert len(capped.content) == MAX_SOURCE_CHARS


def test_hybrid_provider_lists_fused_hits_in_rank_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        neural = b"neural" in request.content
        hits = [_hit("b", "B."), _hit("c", "C.")] if neural else [_hit("a", "A."), _hit("b", "B.")]
        return httpx.Response(200, json={"hits": {"hits": hits}})

    provider = HybridOpenSearchProvider(
        ENDPOINT, "docs", semantic_field="v", model_id="m", transport=httpx.MockTransport(handler)
    )
    ids = [source.source_id for source in provider.execute("q").documents]
    assert ids[0] == "b" and set(ids) == {"a", "b", "c"}


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request: pytest.FixtureRequest
) -> TestClient:
    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    store = AuditTraceStore(str(tmp_path / "audit.sqlite3"), mac_keys=())
    request.addfinalizer(store.close)
    monkeypatch.setattr(app_module, "audit_store", store)
    monkeypatch.setattr(app_module.app, "middleware_stack", None)
    return TestClient(app_module.app)


def _audit(client: TestClient, monkeypatch: pytest.MonkeyPatch, *hits: dict[str, Any]) -> Any:
    monkeypatch.setattr(app_module, "engine", Attractor(search_provider=_provider(*hits)))
    response = client.post("/v2/audit", json={"query": "receita da Vértice", "claims": [CLAIM]})
    assert response.status_code == 200, response.text
    return response.json()


def test_two_independent_hits_are_two_sources(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _audit(
        client,
        monkeypatch,
        _hit("a", "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024."),
        _hit("b", "Em 2024, a receita da Vértice foi de 40 milhões de reais, informou a agência."),
    )
    assert len(body["documents"]) == 2
    assert body["results"][0]["verdict"] == "verified"


def test_a_contradicting_hit_is_seen(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    body = _audit(
        client,
        monkeypatch,
        _hit("a", "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024."),
        _hit("b", "A receita da Vértice foi de 70 milhões de reais em 2024."),
    )
    assert body["results"][0]["verdict"] == "conflicting"


def test_hits_from_the_same_url_are_one_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://mirror.example/balanco"
    body = _audit(
        client,
        monkeypatch,
        _hit(
            "a",
            "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024.",
            url=url,
        ),
        _hit(
            "b",
            "Em 2024, a receita da Vértice foi de 40 milhões de reais, informou a agência.",
            url=url,
        ),
    )
    assert len(body["documents"]) == 2
    assert body["results"][0]["verdict"] == "partially_supported"


def test_a_relevant_hit_after_2000_characters_is_not_lost(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _audit(
        client,
        monkeypatch,
        _hit("filler", "Texto de preenchimento sem relação. " * 80),
        _hit("a", "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024."),
    )
    assert body["results"][0]["verdict"] == "partially_supported"


def test_no_hits_means_no_independent_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _audit(client, monkeypatch)
    assert body["documents"] == []
    assert body["results"][0]["abstention_reason"] == "no_independent_source"
