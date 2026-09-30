import os

from providers.base import Provider
from providers.http_search import HttpSearchProvider
from providers.mock import MockProvider
from providers.openai_compatible import OpenAICompatibleProvider


def build_search_provider() -> HttpSearchProvider | None:
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
