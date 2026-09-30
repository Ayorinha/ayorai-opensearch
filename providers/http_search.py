import json
from urllib import error, parse, request\nfrom urllib.parse import urlparse

from providers.base import Provider, ProviderResponse


class HttpSearchProvider(Provider):
    """Generic JSON search adapter.

    The endpoint contract is intentionally small so real search vendors can be
    added without coupling the core engine to one provider.
    """

    id = "http-search"
    capabilities = frozenset({"search", "research", "evidence"})

    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    def execute(self, prompt: str) -> ProviderResponse:
        if urlparse(self.endpoint).scheme != "https":\n            raise ValueError("Search endpoint must use HTTPS")\n        query = parse.urlencode({"q": prompt})
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(f"{self.endpoint}?{query}", headers=headers)
        try:
            with request.urlopen(req, timeout=30)  # nosec B310 - endpoint is HTTPS-only as response:
                data = json.load(response)
        except error.URLError as exc:
            raise RuntimeError(f"Search request failed: {exc}") from exc
        text = json.dumps(data, ensure_ascii=False)
        return ProviderResponse(text=text, source=self.endpoint, excerpt=text[:1000])
