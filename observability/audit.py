from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    event: str
    timestamp: datetime
    metadata: dict[str, str]


class AuditLog:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, trace_id: str, event: str, metadata: dict[str, str] | None = None) -> None:
        self.events.append(
            AuditEvent(
                trace_id=trace_id,
                event=event,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata or {},
            )
        )
