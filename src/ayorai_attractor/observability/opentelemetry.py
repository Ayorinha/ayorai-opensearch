"""Optional OpenTelemetry adapter for the provider-neutral TraceSink.

The core tracing contract remains dependency-free. This adapter turns each
immutable TraceEvent into a short-lived OpenTelemetry span event, preserving
the ATTRACTOR trace identifier as an explicit attribute without allowing
telemetry to affect verification semantics.
"""

from __future__ import annotations

from typing import Any

from .tracing import TraceEvent


class OpenTelemetrySink:
    """Export TraceSink events through the OpenTelemetry tracing API."""

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
