import os

import httpx

from providers.base import ProviderResponse


class OpenSearchProvider:
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
