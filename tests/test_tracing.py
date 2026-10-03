from dataclasses import dataclass, field

import pytest

from ayorai_attractor.observability.tracing import TraceContext, TraceEvent


def test_trace_context_records_stable_event_snapshot() -> None:
    trace = TraceContext(trace_id="tr_test")
    trace.event("request.started", mode="balanced", tenant="t1")
    trace.event("verification.completed", verdict="supported")

    assert trace.trace_id == "tr_test"
    assert trace.snapshot() == (
        trace.snapshot()[0],
        trace.snapshot()[1],
    )
    assert trace.snapshot()[0].name == "request.started"
    assert trace.snapshot()[0].attributes == (
        ("mode", "balanced"),
        ("tenant", "t1"),
    )


def test_trace_context_rejects_blank_event_name() -> None:
    trace = TraceContext(trace_id="tr_test")

    with pytest.raises(ValueError, match="event name must not be blank"):
        trace.event(" ")


@dataclass
class RecordingSink:
    events: list[tuple[str, TraceEvent]] = field(default_factory=list)

    def emit(self, trace_id: str, event: TraceEvent) -> None:
        self.events.append((trace_id, event))


def test_trace_context_exports_events_without_changing_snapshot() -> None:
    sink = RecordingSink()
    trace = TraceContext(trace_id="tr_test", sink=sink)

    trace.event("provider.ready", model="local")
    trace.event("verification.completed", status="supported")

    assert [event.name for _, event in sink.events] == [
        "provider.ready",
        "verification.completed",
    ]
    assert all(trace_id == "tr_test" for trace_id, _ in sink.events)
    assert tuple(event for _, event in sink.events) == trace.snapshot()


class FakeSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, str] = {}

    def __enter__(self) -> "FakeSpan":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value


@dataclass
class FakeTracer:
    spans: list[FakeSpan] = field(default_factory=list)

    def start_as_current_span(self, name: str) -> FakeSpan:
        span = FakeSpan(name)
        self.spans.append(span)
        return span


def test_opentelemetry_sink_exports_trace_event_without_core_dependency() -> None:
    from ayorai_attractor.observability.tracing import OpenTelemetrySink

    tracer = FakeTracer()
    sink = OpenTelemetrySink(tracer=tracer)
    sink.emit(
        "tr_test",
        TraceEvent(
            "verification.completed",
            (("status", "supported"),),
        ),
    )

    assert len(tracer.spans) == 1
    assert tracer.spans[0].name == "ayorai.verification.completed"
    assert tracer.spans[0].attributes == {
        "ayorai.trace_id": "tr_test",
        "ayorai.event_name": "verification.completed",
        "ayorai.status": "supported",
    }
