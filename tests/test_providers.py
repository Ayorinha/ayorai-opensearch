import pytest

from providers.factory import build_default_provider
from providers.mock import MockProvider


def test_default_provider_is_safe_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTRACTOR_PROVIDER", raising=False)
    provider = build_default_provider()
    assert isinstance(provider, MockProvider)


def test_unknown_provider_fails_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "does-not-exist")
    with pytest.raises(ValueError, match="Unsupported"):
        build_default_provider()


def test_openai_provider_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "openai-compatible")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = build_default_provider()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider.execute("test")



def test_search_provider_requires_https() -> None:
    from providers.http_search import HttpSearchProvider

    provider = HttpSearchProvider("http://example.com/search")
    with pytest.raises(ValueError, match="HTTPS"):
        provider.execute("test")



def test_opensearch_provider_requires_https() -> None:
    from providers.opensearch import OpenSearchProvider

    try:
        OpenSearchProvider("http://localhost:9200", "documents")
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("insecure OpenSearch endpoint was accepted")
