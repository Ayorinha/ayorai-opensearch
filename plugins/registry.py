from dataclasses import dataclass, field


@dataclass
class Plugin:
    id: str
    capabilities: set[str] = field(default_factory=set)
    enabled: bool = True
    trust_level: str = "untrusted"


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.id] = plugin

    def discover(self, capability: str) -> list[Plugin]:
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.enabled and capability in plugin.capabilities
        ]

    def disable(self, plugin_id: str) -> None:
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = False
