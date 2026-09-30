from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from ayorai_attractor.plugins.registry import Plugin, PluginRegistry


@dataclass(frozen=True)
class ToolResult:
    plugin_id: str
    ok: bool
    output: Any
    latency_ms: float


class MCPGateway:
    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self.registry = registry or PluginRegistry()
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(
        self,
        plugin: Plugin,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        self.registry.register(plugin)
        self._handlers[plugin.id] = handler

    def execute(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        trusted_only: bool = True,
    ) -> ToolResult:
        candidates = self.registry.discover(
            capability,
            trusted_only=trusted_only,
        )
        if not candidates:
            raise LookupError(f"No enabled plugin provides capability '{capability}'")

        plugin = candidates[0]
        handler = self._handlers.get(plugin.id)
        if handler is None:
            raise LookupError(f"No handler registered for plugin '{plugin.id}'")

        started = monotonic()
        try:
            output = handler(payload)
        except Exception as exc:
            return ToolResult(
                plugin_id=plugin.id,
                ok=False,
                output=str(exc),
                latency_ms=(monotonic() - started) * 1000,
            )

        return ToolResult(
            plugin_id=plugin.id,
            ok=True,
            output=output,
            latency_ms=(monotonic() - started) * 1000,
        )
