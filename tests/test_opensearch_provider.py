import json
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from ayorai_attractor.providers import _http
from ayorai_attractor.providers import opensearch as opensearch_module
from ayorai_attractor.providers.opensearch import (
    HybridOpenSearchProvider,
    OpenSearchProvider,
    ResponseDeadlineError,
    ResponseTooLargeError,
    UnsupportedEncodingError,
)

ENDPOINT = "https://search.example.test"


def _transport(
    handler: Callable[[httpx.Request], httpx.Response], seen: list[httpx.Request]
) -> httpx.MockTransport:
    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return httpx.MockTransport(record)


def _hits(*hits: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"hits": {"hits": list(hits)}})


def test_opensearch_builds_read_only_query_and_auth_header() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        lambda _: _hits(
            {"_source": {"title": "Doc", "content": "Evidence"}},
            {"_source": {"title": "Doc 2", "content": "More evidence"}},
        ),
        seen,
    )

    response = OpenSearchProvider(
        ENDPOINT, "documents", api_key="secret", timeout=3.5, transport=transport
    ).execute("RAG verification")

    (request,) = seen
    assert request.method == "POST"
    assert str(request.url) == "https://search.example.test/documents/_search"
    assert json.loads(request.content) == {
        "size": 5,
        "query": {
            "multi_match": {
                "query": "RAG verification",
                "fields": ["title^2", "content"],
            }
        },
    }
    assert request.headers["Authorization"] == "ApiKey secret"
    assert request.headers["Accept"] == "application/json"
    assert request.extensions["timeout"]["read"] == 3.5
    assert response.text == "Doc: Evidence\n\nDoc 2: More evidence"
    assert response.independent is True


def test_opensearch_omits_auth_when_key_is_absent() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(lambda _: _hits(), seen)

    response = OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")

    assert "Authorization" not in seen[0].headers
    assert seen[0].headers["Accept"] == "application/json"
    assert response.text == "OpenSearch returned no matching documents."


def test_opensearch_propagates_http_errors() -> None:
    transport = _transport(lambda _: httpx.Response(503), [])

    with pytest.raises(httpx.HTTPStatusError):
        OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")


def test_opensearch_refuses_redirects_so_the_key_stays_with_the_endpoint() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "search.example.test":
            return httpx.Response(302, headers={"Location": "http://other.example.test/x"})
        return _hits()

    transport = _transport(handler, seen)
    with pytest.raises(httpx.HTTPStatusError):
        OpenSearchProvider(ENDPOINT, "documents", api_key="secret", transport=transport).execute(
            "query"
        )
    assert [request.url.host for request in seen] == ["search.example.test"]


def test_opensearch_accepts_a_body_at_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"hits": {"hits": []}}).encode()
    monkeypatch.setattr(_http, "MAX_RESPONSE_BYTES", len(body))
    transport = _transport(lambda _: httpx.Response(200, content=body), [])

    response = OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")

    assert response.text == "OpenSearch returned no matching documents."


def test_opensearch_rejects_a_body_above_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"hits": {"hits": []}}).encode()
    monkeypatch.setattr(_http, "MAX_RESPONSE_BYTES", len(body) - 1)
    transport = _transport(lambda _: httpx.Response(200, content=body), [])

    with pytest.raises(ResponseTooLargeError):
        OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")


def test_opensearch_stops_reading_an_endless_body() -> None:
    produced = 0

    def endless() -> Iterator[bytes]:
        nonlocal produced
        chunk = b"x" * 65536
        while True:
            produced += len(chunk)
            yield chunk

    transport = _transport(lambda _: httpx.Response(200, content=endless()), [])

    with pytest.raises(ResponseTooLargeError):
        OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")
    # Reading stops just past the limit instead of buffering the whole stream.
    assert _http.MAX_RESPONSE_BYTES < produced <= _http.MAX_RESPONSE_BYTES + 65536


def test_opensearch_requests_an_uncompressed_answer() -> None:
    seen: list[httpx.Request] = []
    OpenSearchProvider(
        ENDPOINT, "documents", transport=_transport(lambda _: _hits(), seen)
    ).execute("query")
    assert seen[0].headers["Accept-Encoding"] == "identity"


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "GZIP "])
def test_opensearch_refuses_a_compressed_answer_before_decoding(encoding: str) -> None:
    decoded: list[bytes] = []

    def body() -> Iterator[bytes]:
        decoded.append(b"read")
        yield b"\x1f\x8b"

    transport = _transport(
        lambda _: httpx.Response(200, content=body(), headers={"Content-Encoding": encoding}), []
    )
    with pytest.raises(UnsupportedEncodingError):
        OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")
    assert decoded == []  # the body is never read


@pytest.mark.parametrize("encoding", ["identity", ""])
def test_opensearch_accepts_identity_encoding(encoding: str) -> None:
    transport = _transport(
        lambda _: httpx.Response(
            200,
            content=json.dumps({"hits": {"hits": []}}).encode(),
            headers={"Content-Encoding": encoding},
        ),
        [],
    )
    response = OpenSearchProvider(ENDPOINT, "documents", transport=transport).execute("query")
    assert response.text == "OpenSearch returned no matching documents."


def test_opensearch_enforces_a_total_deadline_across_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(opensearch_module, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    def drip() -> Iterator[bytes]:
        while True:
            clock[0] += 0.5  # each chunk arrives within the per-read timeout
            yield b" "

    transport = _transport(lambda _: httpx.Response(200, content=drip()), [])
    with pytest.raises(ResponseDeadlineError):
        OpenSearchProvider(ENDPOINT, "documents", timeout=2.0, transport=transport).execute("query")
    assert clock[0] <= 1000.0 + 2.0 + 0.5


def test_hybrid_opensearch_fuses_lexical_and_neural_hits() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if len(seen) == 1:
            return _hits(
                {"_id": "a", "_score": 3.0, "_source": {"title": "A", "content": "lexical"}},
                {"_id": "b", "_score": 2.0, "_source": {"title": "B", "content": "both"}},
            )
        return _hits(
            {"_id": "b", "_score": 5.0, "_source": {"title": "B", "content": "both"}},
            {"_id": "c", "_score": 4.0, "_source": {"title": "C", "content": "semantic"}},
        )

    response = HybridOpenSearchProvider(
        ENDPOINT,
        "documents",
        semantic_field="embedding",
        model_id="model-1",
        transport=_transport(handler, seen),
    ).execute("verification")

    queries = [json.loads(request.content) for request in seen]
    assert queries[0]["query"]["multi_match"]["query"] == "verification"
    assert queries[1]["query"]["neural"]["embedding"]["model_id"] == "model-1"
    assert response.text.startswith("B: both")
    assert "A: lexical" in response.text
    assert "C: semantic" in response.text
