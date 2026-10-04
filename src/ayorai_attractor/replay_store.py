"""Content-addressed replay persistence for R4.

Replay bundles are immutable files named by their SHA-256 digest. Loading a
bundle always re-verifies its digest before returning it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ayorai_attractor.replay import ReplayBundle

_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class ReplayStore:
    def __init__(self, directory: str = ".attractor/replays") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def put(self, bundle: ReplayBundle) -> str:
        target = self.directory / f"{bundle.digest}.json"
        if target.exists():
            existing = self._read(target)
            if existing.digest != bundle.digest:
                raise ValueError("replay digest collision")
            return bundle.digest
        target.write_text(
            json.dumps(
                {
                    "version": bundle.version,
                    "trace_id": bundle.trace_id,
                    "events": list(bundle.events),
                    "digest": bundle.digest,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        return bundle.digest

    def get(self, digest: str) -> ReplayBundle | None:
        if not _DIGEST_RE.fullmatch(digest):
            raise ValueError("invalid replay digest")
        target = self.directory / f"{digest}.json"
        if not target.exists():
            return None
        bundle = self._read(target)
        if bundle.digest != digest:
            raise ValueError("replay digest mismatch")
        return bundle

    @staticmethod
    def _read(path: Path) -> ReplayBundle:
        payload = json.loads(path.read_text(encoding="utf-8"))
        bundle = ReplayBundle(
            version=payload["version"],
            trace_id=payload["trace_id"],
            events=tuple(payload["events"]),
            digest=payload["digest"],
        )
        if not bundle.verify():
            raise ValueError("replay integrity check failed")
        return bundle
