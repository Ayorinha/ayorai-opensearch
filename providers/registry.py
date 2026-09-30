from providers.base import Provider
from providers.mock import MockProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self.register(MockProvider())

    def register(self, provider: Provider) -> None:
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> Provider:
        if provider_id not in self._providers:
            raise ValueError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id]
