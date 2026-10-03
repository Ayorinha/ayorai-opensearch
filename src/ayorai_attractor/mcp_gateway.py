"""Minimal governed tool registry for the R12 MCP boundary.

This module models the security contract without embedding a transport server.
Only explicitly registered handlers can execute; unknown tools are rejected.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


ToolHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_keys: frozenset[str]


class ToolRegistry:
    """Allowlist registry for deterministic, auditable tool dispatch."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolHandler]] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, handler)

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(spec for spec, _ in self._tools.values())

    def invoke(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            spec, handler = self._tools[name]
        except KeyError as exc:
            raise ValueError(f"unknown tool: {name}") from exc
        unknown = set(arguments) - spec.input_keys
        if unknown:
            raise ValueError(f"unsupported arguments: {sorted(unknown)}")
        return dict(handler(arguments))
