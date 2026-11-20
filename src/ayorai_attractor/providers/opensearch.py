import json
import os
import time
from typing import Any

import httpx

from ayorai_attractor.hybrid import RankedHit, rrf_fuse
from ayorai_attractor.providers import _http
from ayorai_attractor.providers.base import Provider, ProviderResponse


class ResponseTooLargeError(httpx.TransportError):
    """The search endpoint answered with a body above the provider limit."""


class UnsupportedEncodingError(httpx.TransportError):
    """The search endpoint compressed its answer although identity was requested.

    Decompression is refused: a small compressed body can expand far beyond the
    size limit inside a single decoded chunk, before the limit is checked.
    """


class ResponseDeadlineError(httpx.TimeoutException):
    """The search answer did not complete within the provider timeout.

    httpx timeouts apply to each network operation, so a server that sends a few
    bytes before every read timeout would otherwise keep the request open forever.
    """


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
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("OpenSearch endpoint must use HTTPS")
        if not index.strip():
            raise ValueError("OpenSearch index must not be empty")
        self.endpoint = endpoint.rstrip("/")
        self.index = index.strip()
        self.api_key = api_key
        self.timeout = timeout
        self._transport = transport

    def _post_search(self, query: dict[str, object]) -> Any:
        """POST a search and decode a JSON body of at most ``_http.MAX_RESPONSE_BYTES``.

        Redirects are refused (the ApiKey header must reach only the configured
        endpoint). The body is read raw and uncompressed (``Accept-Encoding:
        identity``; any other ``Content-Encoding`` is refused) and streamed, so an
        oversized, endless or compressed answer fails as a transport error
        instead of exhausting memory. The whole exchange must finish within
        ``timeout`` seconds, checked between reads; each read is itself bounded
        by ``timeout``, so a request lasts at most about twice ``timeout``.
        """
        headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        limit = _http.MAX_RESPONSE_BYTES
        deadline = time.monotonic() + self.timeout
        with httpx.Client(
            transport=self._transport, timeout=self.timeout, follow_redirects=False
        ) as client:
            with client.stream(
                "POST", f"{self.endpoint}/{self.index}/_search", json=query, headers=headers
            ) as response:
                response.raise_for_status()
                encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
                if encoding not in {"", "identity"}:
                    raise UnsupportedEncodingError(
                        f"search response uses Content-Encoding {encoding!r}; "
                        "only identity is accepted",
                        request=response.request,
                    )
                body = bytearray()
                for chunk in response.iter_bytes():  # identity only: no decoding
                    if time.monotonic() > deadline:
                        raise ResponseDeadlineError(
                            f"search response took longer than {self.timeout} s",
                            request=response.request,
                        )
                    body += chunk
                    if len(body) > limit:
                        raise ResponseTooLargeError(
                            f"search response exceeds {limit} bytes", request=response.request
                        )
        return json.loads(bytes(body))

    def execute(self, query: str) -> ProviderResponse:
        payload: dict[str, object] = {
            "size": 5,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],
                }
            },
        }
        body = self._post_search(payload)
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
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(endpoint, index, api_key=api_key, timeout=timeout, transport=transport)
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
        by_id = {str(hit.get("_id")): hit for hit in [*lexical, *semantic] if hit.get("_id")}
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
        body = self._post_search(query)
        return list(body.get("hits", {}).get("hits", []))
