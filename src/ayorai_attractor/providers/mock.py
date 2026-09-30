from ayorai_attractor.providers.base import Provider, ProviderResponse


class MockProvider(Provider):
    id = "mock"
    capabilities = frozenset({"reasoning", "research", "critique", "verification"})

    def execute(self, prompt: str) -> ProviderResponse:
        return ProviderResponse(
            text=f"Deterministic analysis generated for: {prompt}",
            source="local://mock-provider",
            excerpt="Local deterministic provider; not an external factual source.",
        )
