import os

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
