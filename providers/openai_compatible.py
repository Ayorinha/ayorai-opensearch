import json
import os
from urllib import error, request

from providers.base import Provider, ProviderResponse


class OpenAICompatibleProvider(Provider):
    """Minimal OpenAI-compatible chat provider using the Python standard library."""

    id = "openai-compatible"
    capabilities = frozenset({"reasoning", "research", "coding", "critique"})

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("ATTRACTOR_MODEL", "gpt-5")

    def execute(self, prompt: str) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.load(response)
        except error.URLError as exc:
            raise RuntimeError(f"Provider request failed: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Provider returned an invalid chat response") from exc
        return ProviderResponse(text=str(text), source=self.base_url)
