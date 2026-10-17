"""Registry of search/LLM provider metadata.

Status: experimental — fora do escopo verificado. Ver docs/TRACEABILITY-MASTER.md.
Not used by the verification pipeline, the Judge or the public API; the interface may
change without a deprecation period. See docs/EXPERIMENTAL-MODULES.md.
"""

from dataclasses import dataclass, field


@dataclass
class ProviderMetadata:
    id: str
    category: str
    capabilities: set[str] = field(default_factory=set)
    enabled: bool = True
    health: str = "unknown"
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    cost_hint: float | None = None


class ProviderCatalog:
    def __init__(self) -> None:
        self.providers: dict[str, ProviderMetadata] = {}

    def register(self, metadata: ProviderMetadata) -> None:
        self.providers[metadata.id] = metadata

    def by_capability(self, capability: str) -> list[ProviderMetadata]:
        return [
            item
            for item in self.providers.values()
            if item.enabled and capability in item.capabilities
        ]
