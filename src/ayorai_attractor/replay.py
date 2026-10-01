"""Content-addressed replay bundle for R4 provenance and reproducibility."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReplayBundle:
    version: str
    trace_id: str
    events: tuple[dict[str, Any], ...]
    digest: str

    @classmethod
    def build(
        cls,
        trace_id: str,
        events: list[dict[str, Any]],
        version: str = "r4-v1",
    ) -> "ReplayBundle":
        payload = {
            "version": version,
            "trace_id": trace_id,
            "events": events,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return cls(version, trace_id, tuple(events), digest)

    def verify(self) -> bool:
        rebuilt = ReplayBundle.build(
            self.trace_id,
            list(self.events),
            version=self.version,
        )
        return rebuilt.digest == self.digest
