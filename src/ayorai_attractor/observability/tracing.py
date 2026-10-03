"""Provider-neutral tracing context and export boundary.

The core deliberately has no telemetry dependency. A runtime adapter can
implement TraceSink for OpenTelemetry or another backend without changing
verification semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
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


class OpenTelemetrySink:
    """Optional OpenTelemetry adapter for the provider-neutral TraceSink."""

    def __init__(
        self,
        tracer: Any | None = None,
        *,
        instrumentation_name: str = "ayorai-attractor",
    ) -> None:
        if tracer is None:
            try:
                from opentelemetry import trace
            except ImportError as exc:
                raise RuntimeError(
                    "OpenTelemetry support requires the optional 'telemetry' extra"
                ) from exc
            tracer = trace.get_tracer(instrumentation_name)
        self._tracer = tracer

    def emit(self, trace_id: str, event: TraceEvent) -> None:
        span_name = f"ayorai.{event.name}"
        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("ayorai.trace_id", trace_id)
            span.set_attribute("ayorai.event_name", event.name)
            for key, value in event.attributes:
                span.set_attribute(f"ayorai.{key}", value)
