import statistics
import sys
import tempfile
import time
from pathlib import Path

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationEvent, VerificationLog


def ev(n):
    return VerificationEvent(
        input_sha256=f"{n:064x}",
        output_sha256=f"{n + 1:064x}",
        rules_sha256="a" * 64,
        decision_state="DECIDED",
        verdict="SUPPORTED",
        client="c",
        received_at="2026-11-22T00:00:00Z",
        software_id="perf/1",
    )


N = 5000
w = []
v = []
r = []
for _rep in range(3):
    with tempfile.TemporaryDirectory() as t:
        log = VerificationLog(str(Path(t) / "p.sqlite3"), NoteSigner("perf.example/log", bytes(32)))
        t0 = time.perf_counter()
        for i in range(N):
            log.append(ev(i), idempotency_key=f"k-{i}")
        w.append((time.perf_counter() - t0) / N * 1000)
        t0 = time.perf_counter()
        assert log.verify_log()["valid"]
        v.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        for i in range(0, N, 10):
            log.append(ev(i), idempotency_key=f"k-{i}")
        r.append((time.perf_counter() - t0) / (N // 10) * 1000)
        log.close()
print(
    sys.argv[1],
    f"append {statistics.median(w):.3f} ms/event",
    f"| verify_log {statistics.median(v):.2f} s",
    f"| retry {statistics.median(r):.3f} ms",
)
