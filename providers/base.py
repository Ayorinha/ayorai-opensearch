from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    source: str | None = None
    excerpt: str | None = None
    independent: bool = False


class Provider(ABC):
    id = "unknown"
    capabilities: frozenset[str] = frozenset()

    @abstractmethod
    def execute(self, prompt: str) -> ProviderResponse:
        raise NotImplementedError
