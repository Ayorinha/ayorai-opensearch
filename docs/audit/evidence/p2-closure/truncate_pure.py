import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tamper_bench as tb

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationLog

rng = random.Random(11)
n = 20
det_open = det_reopen = 0
with tempfile.TemporaryDirectory() as tmp:
    for i in range(n):
        p = str(Path(tmp) / f"t{i}.sqlite3")
        log, live, erased = tb.build(p, rng)
        for k in range(3):  # events after the erasures: tail is a plain event
            log.append(tb.event(10_000 + k))
        tb.t_truncate_tail(p, rng, live, erased)
        det_open += not log.verify_log()["valid"]
        log.close()
        log = VerificationLog(p, NoteSigner(tb.ORIGIN, tb.SEED))
        det_reopen += not log.verify_log()["valid"]
        log.close()
print(
    sys.argv[1],
    f"tail truncation (plain event): detected open={det_open}/{n} reopen={det_reopen}/{n}",
)
