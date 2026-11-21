"""Write the input of ``verify_receipts.go.txt`` from a fresh verify log.

Usage: ``python tests/auditlog/vectors/make_receipts_input.py > receipts.json``.
The log uses a fixed test seed; nothing here is a production key.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationEvent, VerificationLog

ORIGIN = "attractor.example/verify-log"
SEED = bytes(range(32))


def _event(n: int) -> VerificationEvent:
    return VerificationEvent(
        input_sha256=f"{n:064x}",
        output_sha256=f"{n + 1:064x}",
        rules_sha256="a" * 64,
        decision_state="DECIDED",
        verdict="SUPPORTED" if n % 2 else "NOT_SUPPORTED",
        client="client-a",
        received_at="2026-11-21T00:00:00Z",
        software_id="ayorai-opensearch/vector",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with VerificationLog(str(Path(tmp) / "v.sqlite3"), NoteSigner(ORIGIN, SEED)) as log:
            receipts = [log.append(_event(n)) for n in range(5)]
            old = log.latest_checkpoint()
            receipts += [log.append(_event(n)) for n in range(5, 13)]
            erased = log.erase(2, "2026-11-21T00:00:01Z")
            assert erased == 13
            output = {
                "verifier_key": NoteSigner(ORIGIN, SEED).verifier_key,
                "receipts": receipts,
                "consistency": {
                    "old_checkpoint": old,
                    "new_checkpoint": log.latest_checkpoint(),
                    "proof": log.consistency(5),
                },
            }
    json.dump(output, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
