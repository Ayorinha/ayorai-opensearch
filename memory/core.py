from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class MemoryRecord:
    key: str
    value: str
    source: str
    confidence: float
    created_at: datetime
    last_verified: datetime | None = None


class MemoryStore:
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def put(self, key: str, value: str, source: str, confidence: float) -> None:
        self._records[key] = MemoryRecord(
            key=key,
            value=value,
            source=source,
            confidence=confidence,
            created_at=datetime.now(timezone.utc),
        )

    def get(self, key: str) -> MemoryRecord | None:
        return self._records.get(key)
