import json
from types import SimpleNamespace
from typing import Any

import pytest

from ayorai_attractor.providers.base import Provider, ProviderResponse
from ayorai_attractor.providers.http_search import HttpSearchProvider
from ayorai_attractor.providers.mock import MockProvider
from ayorai_attractor.providers.openai_compatible import OpenAICompatibleProvider
from ayorai_attractor.providers.opensearch import OpenSearchProvider


def assert_provider_contract(provider: Provider) -> None:
    assert provider.id
    assert provider.capabilities
    assert isinstance(provider.capabilities, frozenset)
    assert all(isinstance(item, str) and item for item in provider.capabilities)


def test_mock_provider_contract_and_metadata() -> None:
    provider = MockProvider()
    assert_provider_contract(provider)

    response = provider.execute("test")
    assert isinstance(response, ProviderResponse)
    assert response.text
    assert response.source == "local://mock-provider"
    assert response.excerpt
    assert response.independent is False


@pytest.mark.parametrize(
    ("provider", "expected_capabilities"),
    [
        (OpenAICompatibleProvider(api_key="test"), {"reasoning", "research", "coding", "critique"}),
        (HttpSearchProvider("https://example.test/search"), {"search", "research", "evidence"}),
        (OpenSearchProvider("https://example.test", "documents"), {"search", "evidence"}),
    ],
)
def test_network_provider_capability_contract(
    provider: Provider,
    expected_capabilities: set[str],
) -> None:
    assert_provider_contract(provider)
    assert provider.capabilities == frozenset(expected_capabilities)


def test_openai_compatible_response_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"choices": [{"message": {"content": "answer"}}]}
            ).encode()

    monkeypatch.setattr(
        "ayorai_attractor.providers.openai_compatible.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )
    response = OpenAICompatibleProvider(api_key="test").execute("query")
    assert response.text == "answer"
    assert response.source == "https://api.openai.com/v1"
    assert response.excerpt is None
    assert response.independent is False


def test_http_search_response_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"results": [{"title": "doc"}]}).encode()

    monkeypatch.setattr(
        "ayorai_attractor.providers.http_search.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )
    response = HttpSearchProvider("https://example.test/search").execute("query")
    assert response.source == "https://example.test/search"
    assert response.excerpt == response.text
    assert response.independent is True


def test_opensearch_response_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"hits": {"hits": [{"_source": {"title": "Doc", "content": "text"}}]}},
    )
    monkeypatch.setattr(
        "ayorai_attractor.providers.opensearch.httpx.post",
        lambda *args, **kwargs: fake,
    )
    response = OpenSearchProvider("https://example.test", "documents").execute("query")
    assert response.text == "Doc: text"
    assert response.source == "https://example.test/documents"
    assert response.excerpt == "Doc: text"
    assert response.independent is True
