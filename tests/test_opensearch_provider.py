from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from ayorai_attractor.providers.opensearch import OpenSearchProvider


def test_opensearch_builds_read_only_query_and_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> SimpleNamespace:
        captured["url"] = args[0]
        captured["json"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        captured["timeout"] = kwargs["timeout"]
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "hits": {
                    "hits": [
                        {"_source": {"title": "Doc", "content": "Evidence"}},
                        {"_source": {"title": "Doc 2", "content": "More evidence"}},
                    ]
                }
            },
        )

    monkeypatch.setattr(
        "ayorai_attractor.providers.opensearch.httpx.post",
        fake_post,
    )

    response = OpenSearchProvider(
        "https://search.example.test",
        "documents",
        api_key="secret",
        timeout=3.5,
    ).execute("RAG verification")

    assert captured["url"] == "https://search.example.test/documents/_search"
    assert captured["json"] == {
        "size": 5,
        "query": {
            "multi_match": {
                "query": "RAG verification",
                "fields": ["title^2", "content"],
            }
        },
    }
    assert captured["headers"]["Authorization"] == "ApiKey secret"
    assert captured["headers"]["Accept"] == "application/json"
    assert captured["timeout"] == 3.5
    assert response.text == "Doc: Evidence\n\nDoc 2: More evidence"
    assert response.independent is True


def test_opensearch_omits_auth_when_key_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> SimpleNamespace:
        captured["headers"] = kwargs["headers"]
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"hits": {"hits": []}},
        )

    monkeypatch.setattr(
        "ayorai_attractor.providers.opensearch.httpx.post",
        fake_post,
    )

    response = OpenSearchProvider("https://search.example.test", "documents").execute("query")

    assert captured["headers"] == {"Accept": "application/json"}
    assert response.text == "OpenSearch returned no matching documents."


def test_opensearch_propagates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://search.example.test/documents/_search")
    error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=httpx.Response(503, request=request),
    )

    def fake_post(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(raise_for_status=lambda: (_ for _ in ()).throw(error))

    monkeypatch.setattr(
        "ayorai_attractor.providers.opensearch.httpx.post",
        fake_post,
    )

    with pytest.raises(httpx.HTTPStatusError):
        OpenSearchProvider("https://search.example.test", "documents").execute("query")
