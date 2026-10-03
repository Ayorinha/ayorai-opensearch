from ayorai_attractor.observability.tracing import TraceContext


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

    try:
        trace.event(" ")
    except ValueError as exc:
        assert str(exc) == "event name must not be blank"
    else:
        raise AssertionError("blank event name was accepted")
