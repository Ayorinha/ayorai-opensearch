from ayorai_attractor.mcp_gateway.gateway import MCPGateway
from ayorai_attractor.plugins.registry import Plugin


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


def test_gateway_prefers_healthy_low_latency_trusted_plugin() -> None:
    gateway = MCPGateway()
    gateway.register(
        Plugin(
            id="slow",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=50,
        ),
        lambda _: "slow",
    )
    gateway.register(
        Plugin(
            id="fast",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=5,
        ),
        lambda _: "fast",
    )
    assert gateway.execute("search", {}).output == "fast"


def test_gateway_converts_handler_failure_to_structured_result() -> None:
    gateway = MCPGateway()
    gateway.register(
        Plugin(id="broken", capabilities={"search"}, trust_level="trusted"),
        lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    result = gateway.execute("search", {})
    assert result.ok is False
    assert result.output == "boom"
