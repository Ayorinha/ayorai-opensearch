"""Pin the behaviour of the experimental modules (docs/EXPERIMENTAL-MODULES.md)."""

from __future__ import annotations

import builtins
from contextlib import contextmanager
from datetime import UTC
from typing import Any

import pytest
from pydantic import ValidationError

from ayorai_attractor.memory.core import MemoryStore
from ayorai_attractor.observability.audit import AuditLog
from ayorai_attractor.observability.opentelemetry import OpenTelemetrySink
from ayorai_attractor.observability.tracing import TraceEvent
from ayorai_attractor.providers.catalog import ProviderCatalog, ProviderMetadata
from ayorai_attractor.research_contract import ResearchContract
from ayorai_attractor.security.policy import SecurityPolicy, ToolPolicy


def test_memory_store_put_get_and_overwrite() -> None:
    store = MemoryStore()
    assert store.get("missing") is None
    store.put("k", "v1", source="doc-1", confidence=0.5)
    first = store.get("k")
    assert first is not None
    assert (first.value, first.source, first.confidence) == ("v1", "doc-1", 0.5)
    assert first.created_at.tzinfo is UTC
    assert first.last_verified is None
    store.put("k", "v2", source="doc-2", confidence=0.9)
    second = store.get("k")
    assert second is not None and second.value == "v2"


def test_audit_log_records_events_in_order() -> None:
    log = AuditLog()
    log.record("tr_1", "start")
    log.record("tr_1", "end", {"status": "ok"})
    assert [e.event for e in log.events] == ["start", "end"]
    assert log.events[0].metadata == {}
    assert log.events[1].metadata == {"status": "ok"}
    assert log.events[0].timestamp.tzinfo is UTC
    with pytest.raises(AttributeError):
        log.events[0].event = "changed"  # type: ignore[misc]


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


class _FakeTracer:
    def __init__(self) -> None:
        self.spans: list[tuple[str, _FakeSpan]] = []

    @contextmanager
    def start_as_current_span(self, name: str):  # type: ignore[no-untyped-def]
        span = _FakeSpan()
        self.spans.append((name, span))
        yield span


def test_opentelemetry_sink_exports_event_attributes() -> None:
    tracer = _FakeTracer()
    sink = OpenTelemetrySink(tracer)
    sink.emit("tr_abc", TraceEvent("judge.decided", (("verdict", "SUPPORTED"),)))
    assert len(tracer.spans) == 1
    name, span = tracer.spans[0]
    assert name == "ayorai.judge.decided"
    assert span.attributes == {
        "ayorai.trace_id": "tr_abc",
        "ayorai.event_name": "judge.decided",
        "ayorai.verdict": "SUPPORTED",
    }


def test_opentelemetry_sink_requires_optional_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "opentelemetry" or name.startswith("opentelemetry."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="telemetry"):
        OpenTelemetrySink()


def test_provider_catalog_filters_by_capability_and_enabled() -> None:
    catalog = ProviderCatalog()
    catalog.register(ProviderMetadata("a", "search", {"web"}))
    catalog.register(ProviderMetadata("b", "search", {"web"}, enabled=False))
    catalog.register(ProviderMetadata("c", "llm", {"chat"}))
    assert [p.id for p in catalog.by_capability("web")] == ["a"]
    assert [p.id for p in catalog.by_capability("chat")] == ["c"]
    assert catalog.by_capability("none") == []
    assert catalog.providers["a"].health == "unknown"


def test_research_contract_defaults_and_validation() -> None:
    contract = ResearchContract(question="Qual é o prazo?")
    assert contract.independent_sources_required == 1
    assert contract.uncertainty_required is True
    assert contract.acceptable_sources == []
    with pytest.raises(ValidationError):
        ResearchContract(question="ab")
    with pytest.raises(ValidationError):
        ResearchContract(question="valid", independent_sources_required=-1)
    with pytest.raises(ValidationError):
        ResearchContract(question="valid", max_age_days=-1)


def test_security_policy_denies_by_default() -> None:
    policy = SecurityPolicy()
    assert policy.authorize("shell") is False
    policy.set(ToolPolicy("search", allowed=True))
    policy.set(ToolPolicy("shell", allowed=False))
    assert policy.authorize("search") is True
    assert policy.authorize("shell") is False
    policy.set(ToolPolicy("shell", allowed=True))
    assert policy.authorize("shell") is True
