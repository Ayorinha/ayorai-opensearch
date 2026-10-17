"""In-memory audit event log.

Status: experimental — fora do escopo verificado. Ver docs/TRACEABILITY-MASTER.md.
Not used by the verification pipeline, the Judge or the public API; the interface may
change without a deprecation period. See docs/EXPERIMENTAL-MODULES.md.

This is distinct from the persistent API audit store used by /v1/verify.
"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    event: str
    timestamp: datetime
    metadata: dict[str, str]


class AuditLog:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(
        self,
        trace_id: str,
        event: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.events.append(
            AuditEvent(
                trace_id=trace_id,
                event=event,
                timestamp=datetime.now(UTC),
                metadata=metadata or {},
            )
        )
