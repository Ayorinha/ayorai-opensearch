"""Small provider-neutral tracing context for R14.

The core intentionally has no telemetry dependency. Adapters can export the
immutable event snapshot to OpenTelemetry or another backend without changing
verification semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    name: str
    attributes: tuple[tuple[str, str], ...] = ()


@dataclass
class TraceContext:
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex}")
    _events: list[TraceEvent] = field(default_factory=list, repr=False)

    def event(self, name: str, **attributes: object) -> None:
        if not name.strip():
            raise ValueError("event name must not be blank")
        normalized = tuple(
            sorted((key, str(value)) for key, value in attributes.items())
        )
        self._events.append(TraceEvent(name=name, attributes=normalized))

    def snapshot(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)
