from mcp.gateway import MCPGateway
from plugins.registry import Plugin


def test_gateway_executes_trusted_capability() -> None:
    gateway = MCPGateway()
    gateway.register(
        Plugin(
            id="search",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=10,
        ),
        lambda payload: {"query": payload["query"]},
    )

    result = gateway.execute("search", {"query": "AI"})
    assert result.ok is True
    assert result.output == {"query": "AI"}


def test_gateway_does_not_execute_untrusted_plugin_by_default() -> None:
    gateway = MCPGateway()
    gateway.register(
        Plugin(id="unsafe", capabilities={"search"}, trust_level="untrusted"),
        lambda _: "should not run",
    )

    try:
        gateway.execute("search", {})
    except LookupError as exc:
        assert "No enabled plugin" in str(exc)
    else:
        raise AssertionError("untrusted plugin was executed")
