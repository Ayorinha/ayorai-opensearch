"""Provider configuration is validated at API startup and fails closed."""

import pytest

from ayorai_attractor.providers.factory import validate_provider_configuration

_VARS = (
    "ATTRACTOR_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ATTRACTOR_OPENSEARCH_ENDPOINT",
    "ATTRACTOR_OPENSEARCH_INDEX",
    "ATTRACTOR_SEARCH_ENDPOINT",
)


@pytest.fixture(autouse=True)
def clean_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"ATTRACTOR_PROVIDER": "mock"},
        {"ATTRACTOR_PROVIDER": "openai-compatible", "OPENAI_API_KEY": "test-key"},
        {
            "ATTRACTOR_OPENSEARCH_ENDPOINT": "https://search.test",
            "ATTRACTOR_OPENSEARCH_INDEX": "docs",
        },
        {"ATTRACTOR_SEARCH_ENDPOINT": "https://search.test/q"},
    ],
)
def test_valid_configurations_are_accepted(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str]
) -> None:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    validate_provider_configuration()


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"ATTRACTOR_PROVIDER": "unsupported"}, "Unsupported ATTRACTOR_PROVIDER"),
        ({"ATTRACTOR_PROVIDER": "openai-compatible"}, "OPENAI_API_KEY is required"),
        (
            {
                "ATTRACTOR_PROVIDER": "openai-compatible",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "http://user:s3cr3t@llm.test/v1",
            },
            "OPENAI_BASE_URL must use HTTPS",
        ),
        ({"ATTRACTOR_OPENSEARCH_ENDPOINT": "https://search.test"}, "must be set together"),
        ({"ATTRACTOR_OPENSEARCH_INDEX": "docs"}, "must be set together"),
        (
            {
                "ATTRACTOR_OPENSEARCH_ENDPOINT": "http://search.test",
                "ATTRACTOR_OPENSEARCH_INDEX": "d",
            },
            "must use HTTPS",
        ),
        ({"ATTRACTOR_SEARCH_ENDPOINT": "http://search.test/q"}, "ATTRACTOR_SEARCH_ENDPOINT"),
    ],
)
def test_invalid_configurations_fail_without_echoing_secrets(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], message: str
) -> None:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message) as raised:
        validate_provider_configuration()
    assert "s3cr3t" not in str(raised.value)
    assert "test-key" not in str(raised.value)


def test_api_refuses_to_start_with_an_unsupported_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from ayorai_attractor.api.app import app

    monkeypatch.setenv("ATTRACTOR_AUTH_MODE", "off")
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "unsupported")
    with pytest.raises(ValueError, match="Unsupported ATTRACTOR_PROVIDER"):
        with TestClient(app):
            pass
