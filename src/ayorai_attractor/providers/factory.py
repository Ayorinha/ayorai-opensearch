import os
from urllib.parse import urlparse

from ayorai_attractor.providers.base import Provider
from ayorai_attractor.providers.http_search import HttpSearchProvider
from ayorai_attractor.providers.mock import MockProvider
from ayorai_attractor.providers.openai_compatible import OpenAICompatibleProvider
from ayorai_attractor.providers.opensearch import build_opensearch_provider


def build_search_provider() -> Provider | None:
    opensearch = build_opensearch_provider()
    if opensearch is not None:
        return opensearch
    endpoint = os.getenv("ATTRACTOR_SEARCH_ENDPOINT", "").strip()
    if not endpoint:
        return None
    return HttpSearchProvider(endpoint, os.getenv("ATTRACTOR_SEARCH_API_KEY"))


def build_default_provider() -> Provider:
    provider_id = os.getenv("ATTRACTOR_PROVIDER", "mock").strip().lower()
    if provider_id == "openai-compatible":
        return OpenAICompatibleProvider()
    if provider_id != "mock":
        raise ValueError(f"Unsupported ATTRACTOR_PROVIDER: {provider_id}")
    return MockProvider()


def validate_provider_configuration() -> None:
    """Reject at startup a provider configuration that every request would fail on.

    Raises ``ValueError`` without echoing secret values. Checked: a supported
    ``ATTRACTOR_PROVIDER``; for ``openai-compatible``, an HTTPS base URL and an
    ``OPENAI_API_KEY``; OpenSearch endpoint and index set together (a partial
    configuration is otherwise silently ignored); HTTPS search endpoints.
    """
    provider = build_default_provider()
    if isinstance(provider, OpenAICompatibleProvider):
        if urlparse(provider.base_url).scheme != "https":
            raise ValueError("OPENAI_BASE_URL must use HTTPS")
        if not provider.api_key:
            raise ValueError("OPENAI_API_KEY is required when ATTRACTOR_PROVIDER=openai-compatible")
    endpoint = os.getenv("ATTRACTOR_OPENSEARCH_ENDPOINT", "").strip()
    index = os.getenv("ATTRACTOR_OPENSEARCH_INDEX", "").strip()
    if bool(endpoint) != bool(index):
        raise ValueError(
            "ATTRACTOR_OPENSEARCH_ENDPOINT and ATTRACTOR_OPENSEARCH_INDEX must be set together"
        )
    search = build_search_provider()
    if isinstance(search, HttpSearchProvider) and urlparse(search.endpoint).scheme != "https":
        raise ValueError("ATTRACTOR_SEARCH_ENDPOINT must use HTTPS")
