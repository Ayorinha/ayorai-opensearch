"""Content-addressed replay persistence for R4.

Replay bundles are immutable files named by their SHA-256 digest. Storing a
bundle verifies its digest first, so a forged digest can neither name a file
outside the store nor be stored under content it does not match. Files are
written to a temporary file in the same directory and moved into place, so a
crash never leaves a truncated bundle under a valid name. Loading a bundle
always re-verifies its digest before returning it.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from ayorai_attractor.replay import ReplayBundle

_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class ReplayStore:
    def __init__(self, directory: str = ".attractor/replays") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def put(self, bundle: ReplayBundle) -> str:
        if not _DIGEST_RE.fullmatch(bundle.digest) or not bundle.verify():
            raise ValueError("replay bundle digest does not match its content")
        target = self.directory / f"{bundle.digest}.json"
        if target.exists():
            existing = self._read(target)
            if existing.digest != bundle.digest:
                raise ValueError("replay digest collision")
            return bundle.digest
        encoded = json.dumps(
            {
                "version": bundle.version,
                "trace_id": bundle.trace_id,
                "events": list(bundle.events),
                "digest": bundle.digest,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        handle, temporary = tempfile.mkstemp(
            prefix=f".{bundle.digest}.", suffix=".tmp", dir=self.directory
        )
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            # Content-addressed: a concurrent writer of the same digest writes
            # identical bytes, so replacing it is harmless.
            os.replace(temporary, target)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
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
