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
