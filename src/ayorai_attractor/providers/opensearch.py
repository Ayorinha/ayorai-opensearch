import os
from typing import Any

import httpx

from ayorai_attractor.hybrid import RankedHit, rrf_fuse
from ayorai_attractor.providers.base import Provider, ProviderResponse


class OpenSearchProvider(Provider):
    id = "opensearch"
    capabilities = frozenset({"search", "evidence"})
    """Read-only OpenSearch-compatible search adapter."""

    def __init__(
        self,
        endpoint: str,
        index: str,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("OpenSearch endpoint must use HTTPS")
        if not index.strip():
            raise ValueError("OpenSearch index must not be empty")
        self.endpoint = endpoint.rstrip("/")
        self.index = index.strip()
        self.api_key = api_key
        self.timeout = timeout

    def execute(self, query: str) -> ProviderResponse:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        payload = {
            "size": 5,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],
                }
            },
        }
        response = httpx.post(
            f"{self.endpoint}/{self.index}/_search",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        hits = body.get("hits", {}).get("hits", [])
        excerpts = []
        for hit in hits:
            source = hit.get("_source", {})
            title = str(source.get("title", ""))
            content = str(source.get("content", ""))
            excerpts.append(f"{title}: {content}".strip(": "))
        text = "\n\n".join(excerpts) or "OpenSearch returned no matching documents."
        return ProviderResponse(
            text=text,
            source=f"{self.endpoint}/{self.index}",
            excerpt=text[:2000],
            independent=True,
        )


def build_opensearch_provider() -> OpenSearchProvider | None:
    endpoint = os.getenv("ATTRACTOR_OPENSEARCH_ENDPOINT", "").strip()
    index = os.getenv("ATTRACTOR_OPENSEARCH_INDEX", "").strip()
    if not endpoint or not index:
        return None
    return OpenSearchProvider(
        endpoint=endpoint,
        index=index,
        api_key=os.getenv("ATTRACTOR_OPENSEARCH_API_KEY"),
    )



class HybridOpenSearchProvider(OpenSearchProvider):
    """OpenSearch provider combining lexical and neural retrieval with RRF."""

    def __init__(
        self,
        endpoint: str,
        index: str,
        *,
        semantic_field: str,
        model_id: str,
        api_key: str | None = None,
        timeout: float = 10.0,
        rrf_k: int = 60,
        lexical_weight: float = 0.5,
        semantic_weight: float = 0.5,
    ) -> None:
        super().__init__(endpoint, index, api_key=api_key, timeout=timeout)
        if not semantic_field.strip():
            raise ValueError("semantic_field must not be empty")
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        self.semantic_field = semantic_field.strip()
        self.model_id = model_id.strip()
        self.rrf_k = rrf_k
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight

    def execute(self, query: str) -> ProviderResponse:
        lexical = self._search(
            {
                "size": 10,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                    }
                },
            }
        )
        semantic = self._search(
            {
                "size": 10,
                "query": {
                    "neural": {
                        self.semantic_field: {
                            "query_text": query,
                            "model_id": self.model_id,
                        }
                    }
                },
            }
        )
        lexical_hits = [
            RankedHit(str(hit.get("_id", "")), float(hit.get("_score") or 0.0))
            for hit in lexical
            if hit.get("_id")
        ]
        semantic_hits = [
            RankedHit(str(hit.get("_id", "")), float(hit.get("_score") or 0.0))
            for hit in semantic
            if hit.get("_id")
        ]
        fused = rrf_fuse(
            lexical_hits,
            semantic_hits,
            k=self.rrf_k,
            lexical_weight=self.lexical_weight,
            semantic_weight=self.semantic_weight,
        )
        by_id = {
            str(hit.get("_id")): hit
            for hit in [*lexical, *semantic]
            if hit.get("_id")
        }
        excerpts = []
        for ranked in fused[:10]:
            source = by_id[ranked.document_id].get("_source", {})
            title = str(source.get("title", ""))
            content = str(source.get("content", ""))
            excerpts.append(f"{title}: {content}".strip(": "))
        text = "\n\n".join(excerpts) or "OpenSearch returned no matching documents."
        return ProviderResponse(
            text=text,
            source=f"{self.endpoint}/{self.index}",
            excerpt=text[:2000],
            independent=True,
        )

    def _search(self, query: dict[str, object]) -> list[dict[str, Any]]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        response = httpx.post(
            f"{self.endpoint}/{self.index}/_search",
            json=query,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        return list(body.get("hits", {}).get("hits", []))
