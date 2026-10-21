from ayorai_attractor.plugins.registry import Plugin, PluginRegistry


def test_discover_filters_health_enabled_capability_and_trust_and_sorts() -> None:
    registry = PluginRegistry()
    registry.register(
        Plugin(
            id="fast-expensive",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=5.0,
            cost_per_call=2.0,
        )
    )
    registry.register(
        Plugin(
            id="fast-cheap",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=5.0,
            cost_per_call=1.0,
        )
    )
    registry.register(
        Plugin(
            id="slow",
            capabilities={"search"},
            trust_level="trusted",
            latency_ms=10.0,
            cost_per_call=0.5,
        )
    )
    registry.register(
        Plugin(
            id="untrusted",
            capabilities={"search"},
            trust_level="untrusted",
            latency_ms=1.0,
            cost_per_call=0.1,
        )
    )
    registry.register(Plugin(id="disabled", capabilities={"search"}, enabled=False))
    registry.register(Plugin(id="unhealthy", capabilities={"search"}, healthy=False))
    registry.register(Plugin(id="other-capability", capabilities={"audit"}))
    registry.register(Plugin(id="no-metrics", capabilities={"search"}, trust_level="trusted"))

    assert [plugin.id for plugin in registry.discover("search")] == [
        "untrusted",
        "fast-cheap",
        "fast-expensive",
        "slow",
        "no-metrics",
    ]
    assert [plugin.id for plugin in registry.discover("search", trusted_only=True)] == [
        "fast-cheap",
        "fast-expensive",
        "slow",
        "no-metrics",
    ]
    assert registry.discover("missing") == []


def test_disable_and_health_changes_ignore_unknown_ids() -> None:
    registry = PluginRegistry()
    plugin = Plugin(id="searcher", capabilities={"search"})
    registry.register(plugin)

    registry.disable("missing")
    registry.set_health("missing", False)
    assert registry.discover("search") == [plugin]

    registry.disable("searcher")
    assert registry.discover("search") == []
    registry.register(Plugin(id="searcher", capabilities={"search"}))
    registry.set_health("searcher", False)
    assert registry.discover("search") == []
