"""Provider-neutral tracing context and export boundary.

The core deliberately has no telemetry dependency. A runtime adapter can
implement TraceSink for OpenTelemetry or another backend without changing
verification semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class TraceEvent:
    name: str
    attributes: tuple[tuple[str, str], ...] = ()


class TraceSink(Protocol):
    """Minimal side-effect boundary for exporting immutable trace events."""

    def emit(self, trace_id: str, event: TraceEvent) -> None: ...


@dataclass
class TraceContext:
    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex}")
    sink: TraceSink | None = None
    _events: list[TraceEvent] = field(default_factory=list, repr=False)

    def event(self, name: str, **attributes: object) -> None:
        if not name.strip():
            raise ValueError("event name must not be blank")
        normalized = tuple(
            sorted((key, str(value)) for key, value in attributes.items())
        )
        event = TraceEvent(name=name, attributes=normalized)
        self._events.append(event)
        if self.sink is not None:
            self.sink.emit(self.trace_id, event)

    def snapshot(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)
