import os

import pytest

from providers.factory import build_default_provider
from providers.mock import MockProvider


def test_default_provider_is_safe_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTRACTOR_PROVIDER", raising=False)
    provider = build_default_provider()
    assert isinstance(provider, MockProvider)


def test_unknown_provider_fails_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "does-not-exist")
    with pytest.raises(ValueError, match="Unsupported"):
        build_default_provider()


def test_openai_provider_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "openai-compatible")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = build_default_provider()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        provider.execute("test")
