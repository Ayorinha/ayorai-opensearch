import os

from providers.base import Provider
from providers.mock import MockProvider
from providers.openai_compatible import OpenAICompatibleProvider


def build_default_provider() -> Provider:
    provider_id = os.getenv("ATTRACTOR_PROVIDER", "mock").strip().lower()
    if provider_id == "openai-compatible":
        return OpenAICompatibleProvider()
    if provider_id != "mock":
        raise ValueError(f"Unsupported ATTRACTOR_PROVIDER: {provider_id}")
    return MockProvider()
