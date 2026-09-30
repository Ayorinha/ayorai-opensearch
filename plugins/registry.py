from dataclasses import dataclass, field


@dataclass
class Plugin:
    id: str
    capabilities: set[str] = field(default_factory=set)
    enabled: bool = True
    trust_level: str = "untrusted"
    healthy: bool = True
    latency_ms: float | None = None
    cost_per_call: float | None = None


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.id] = plugin

    def discover(self, capability: str, *, trusted_only: bool = False) -> list[Plugin]:
        candidates = [
            plugin
            for plugin in self._plugins.values()
            if plugin.enabled and plugin.healthy and capability in plugin.capabilities
        ]
        if trusted_only:
            candidates = [plugin for plugin in candidates if plugin.trust_level == "trusted"]
        return sorted(candidates, key=lambda plugin: (plugin.latency_ms is None, plugin.latency_ms or 0.0, plugin.cost_per_call is None, plugin.cost_per_call or 0.0))

    def disable(self, plugin_id: str) -> None:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = False

    def set_health(self, plugin_id: str, healthy: bool) -> None:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].healthy = healthy
