from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedSource:
    """One retrieved document, kept apart from the others with its own provenance."""

    content: str
    source: str
    url: str | None = None
    source_id: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    source: str | None = None
    excerpt: str | None = None
    independent: bool = False
    # Search providers list each hit separately so that every hit is adjudicated as
    # its own document with its own provenance (never a concatenation of hits).
    documents: tuple[RetrievedSource, ...] = ()


class Provider(ABC):
    id = "unknown"
    capabilities: frozenset[str] = frozenset()

    @abstractmethod
    def execute(self, prompt: str) -> ProviderResponse:
        raise NotImplementedError
