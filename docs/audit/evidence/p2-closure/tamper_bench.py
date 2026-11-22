"""Tamper-detection benchmark for the ADR-010 verify log.

Run with PYTHONPATH pointing to the src/ of the tree under test.

Each instance builds a fresh log (random size and erasures, fixed seed), tampers the
SQLite file through another connection while the log stays open (the threat model of
verify_log), and records whether verify_log() reports it. Clean logs measure false alarms.
Usage: python tamper_bench.py <label> <out.json>
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

from ayorai_attractor.auditlog.merkle import leaf_hash
from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationEvent, VerificationLog

ORIGIN = "bench.example/verify-log"
SEED = bytes(range(32))
K = 20


def event(n: int) -> VerificationEvent:
    return VerificationEvent(
        input_sha256=f"{n:064x}",
        output_sha256=f"{n + 1:064x}",
        rules_sha256="a" * 64,
        decision_state="DECIDED",
        verdict="SUPPORTED" if n % 2 else "REFUTED",
        client="c",
        received_at="2026-11-22T00:00:00Z",
        software_id="bench/1",
    )


def build(path: str, rng: random.Random) -> tuple[VerificationLog, list[int], list[int]]:
    log = VerificationLog(path, NoteSigner(ORIGIN, SEED))
    n = rng.randint(6, 30)
    events = [log.append(event(i), idempotency_key=f"k-{i}")["index"] for i in range(n)]
    erased = rng.sample(events, k=rng.randint(1, 2))
    for idx in erased:
        log.erase(idx, "2026-11-22T01:00:00Z")
    live = [i for i in events if i not in erased]
    return log, live, erased


def sql(path: str, statement: str, params: tuple = ()) -> None:
    with closing(sqlite3.connect(path)) as c:
        c.execute(statement, params)
        c.commit()


def q(path: str, statement: str, params: tuple = ()) -> list:
    with closing(sqlite3.connect(path)) as c:
        return c.execute(statement, params).fetchall()


def t_record_field(path, rng, live, erased):
    idx = rng.choice(live)
    (rec,) = q(path, "SELECT record FROM vlog_records WHERE idx=?", (idx,))[0]
    data = json.loads(rec)
    data["verdict"] = "REFUTED" if data.get("verdict") != "REFUTED" else "SUPPORTED"
    sql(path, "UPDATE vlog_records SET record=? WHERE idx=?", (json.dumps(data), idx))


def t_salt(path, rng, live, erased):
    sql(path, "UPDATE vlog_records SET salt=? WHERE idx=?", (bytes(32), rng.choice(live)))


def t_delete_record(path, rng, live, erased):
    sql(path, "DELETE FROM vlog_records WHERE idx=?", (rng.choice(live),))


def t_partial_erasure(path, rng, live, erased):
    sql(path, "UPDATE vlog_records SET record=NULL, salt=NULL WHERE idx=?", (rng.choice(live),))


def t_fake_erasure(path, rng, live, erased):
    sql(
        path,
        "UPDATE vlog_records SET record=NULL, salt=NULL, "
        "erased_at='2026-11-22T02:00:00Z' WHERE idx=?",
        (rng.choice(live),),
    )


def t_orphan_record(path, rng, live, erased):
    (mx,) = q(path, "SELECT MAX(idx) FROM vlog_leaves")[0]
    sql(
        path,
        "INSERT INTO vlog_records (idx, salt, record, erased_at) VALUES (?,?,?,NULL)",
        (mx + 100, bytes(32), json.dumps({"schema": "x"})),
    )


def t_restore_erased(path, rng, live, erased):
    sql(
        path,
        "UPDATE vlog_records SET salt=?, record=?, erased_at=NULL WHERE idx=?",
        (bytes(32), json.dumps({"verdict": "SUPPORTED"}), rng.choice(erased)),
    )


def t_erased_at_changed(path, rng, live, erased):
    sql(
        path,
        "UPDATE vlog_records SET erased_at='2030-01-01T00:00:00Z' WHERE idx=?",
        (rng.choice(erased),),
    )


def t_leaf_stale_hash(path, rng, live, erased):
    sql(path, "UPDATE vlog_leaves SET leaf=? WHERE idx=?", (b'{"x":1}', rng.choice(live)))


def t_leaf_rehashed(path, rng, live, erased):
    new = b'{"x":2}'
    sql(
        path,
        "UPDATE vlog_leaves SET leaf=?, leaf_hash=? WHERE idx=?",
        (new, leaf_hash(new), rng.choice(live)),
    )


def t_delete_checkpoint(path, rng, live, erased):
    sizes = [s for (s,) in q(path, "SELECT size FROM vlog_checkpoints")]
    sql(path, "DELETE FROM vlog_checkpoints WHERE size=?", (rng.choice(sizes),))


def t_checkpoint_note(path, rng, live, erased):
    sizes = [s for (s,) in q(path, "SELECT size FROM vlog_checkpoints")]
    size = rng.choice(sizes)
    (note,) = q(path, "SELECT note FROM vlog_checkpoints WHERE size=?", (size,))[0]
    lines = note.split("\n")
    lines[2] = base64.b64encode(bytes(32)).decode()
    sql(path, "UPDATE vlog_checkpoints SET note=? WHERE size=?", ("\n".join(lines), size))


def t_extra_leaf(path, rng, live, erased):
    (mx,) = q(path, "SELECT MAX(idx) FROM vlog_leaves")[0]
    leaf = b'{"schema":"unknown"}'
    sql(
        path,
        "INSERT INTO vlog_leaves (idx, leaf, leaf_hash) VALUES (?,?,?)",
        (mx + 1, leaf, leaf_hash(leaf)),
    )


def t_truncate_tail(path, rng, live, erased):
    # Out of scope for a self-contained check: drop the last leaf with its record and
    # checkpoint. Only an external checkpoint (witness) can reveal it.
    (mx,) = q(path, "SELECT MAX(idx) FROM vlog_leaves")[0]
    sql(path, "DELETE FROM vlog_leaves WHERE idx=?", (mx,))
    sql(path, "DELETE FROM vlog_records WHERE idx=?", (mx,))
    sql(path, "DELETE FROM vlog_checkpoints WHERE size=?", (mx + 1,))


def kd(i):
    return hashlib.sha256(f"c\x00k-{i}".encode()).hexdigest()


def receipt_of(path, i):
    return q(path, "SELECT receipt FROM vlog_idempotency WHERE key_digest=?", (kd(i),))[0][0]


def t_idem_swap_events(path, rng, live, erased):
    a, b = rng.sample(live, 2)
    ra, rb = receipt_of(path, a), receipt_of(path, b)
    sql(path, "UPDATE vlog_idempotency SET receipt=? WHERE key_digest=?", (rb, kd(a)))
    sql(path, "UPDATE vlog_idempotency SET receipt=? WHERE key_digest=?", (ra, kd(b)))


def t_idem_row_index(path, rng, live, erased):
    a, b = rng.sample(live, 2)
    sql(path, "UPDATE vlog_idempotency SET idx=? WHERE key_digest=?", (b, kd(a)))


def t_idem_receipt_verdict(path, rng, live, erased):
    a = rng.choice(live)
    r = json.loads(receipt_of(path, a))
    r["record"]["verdict"] = "SUPPORTED" if r["record"]["verdict"] != "SUPPORTED" else "REFUTED"
    sql(path, "UPDATE vlog_idempotency SET receipt=? WHERE key_digest=?", (json.dumps(r), kd(a)))


def t_idem_receipt_empty(path, rng, live, erased):
    sql(
        path, "UPDATE vlog_idempotency SET receipt='{}' WHERE key_digest=?", (kd(rng.choice(live)),)
    )


def t_idem_dangling(path, rng, live, erased):
    sql(path, "UPDATE vlog_idempotency SET idx=9999 WHERE key_digest=?", (kd(rng.choice(live)),))


def t_idem_duplicate(path, rng, live, erased):
    a = rng.choice(live)
    row = q(
        path, "SELECT input_sha256, idx, receipt FROM vlog_idempotency WHERE key_digest=?", (kd(a),)
    )[0]
    sql(path, "INSERT INTO vlog_idempotency VALUES (?,?,?,?)", ("e" * 64, *row))


def t_idem_erased_residue(path, rng, live, erased):
    # Receipt still holding record and salt after the erasure (state of the code before M2).
    a = rng.choice(erased)
    r = q(path, "SELECT receipt FROM vlog_idempotency WHERE key_digest=?", (kd(a),))[0][0]
    if json.loads(r).get("redacted") is not True:
        return  # older code keeps the residue by itself
    full = {"index": a, "record": {"verdict": "REFUTED", "client": "c"}, "salt": "AAAA"}
    sql(path, "UPDATE vlog_idempotency SET receipt=? WHERE key_digest=?", (json.dumps(full), kd(a)))


def t_idem_rows_swapped(path, rng, live, erased):
    # Out of scope: whole rows exchanged between keys stay self-consistent.
    a, b = rng.sample(live, 2)
    ra = q(
        path, "SELECT input_sha256, idx, receipt FROM vlog_idempotency WHERE key_digest=?", (kd(a),)
    )[0]
    rb = q(
        path, "SELECT input_sha256, idx, receipt FROM vlog_idempotency WHERE key_digest=?", (kd(b),)
    )[0]
    sql(
        path,
        "UPDATE vlog_idempotency SET input_sha256=?, idx=?, receipt=? WHERE key_digest=?",
        (*rb, kd(a)),
    )
    sql(
        path,
        "UPDATE vlog_idempotency SET input_sha256=?, idx=?, receipt=? WHERE key_digest=?",
        (*ra, kd(b)),
    )


CLASSES = {
    "T01_record_field_changed": t_record_field,
    "T02_salt_changed": t_salt,
    "T03_record_row_deleted": t_delete_record,
    "T04_record_nulled_without_erasure": t_partial_erasure,
    "T05_fake_erasure_marker": t_fake_erasure,
    "T06_orphan_record_row": t_orphan_record,
    "T07_erased_record_restored": t_restore_erased,
    "T08_erased_at_changed": t_erased_at_changed,
    "T09_leaf_changed_stale_hash": t_leaf_stale_hash,
    "T10_leaf_changed_rehashed": t_leaf_rehashed,
    "T11_checkpoint_deleted": t_delete_checkpoint,
    "T12_checkpoint_root_forged": t_checkpoint_note,
    "T13_unsigned_leaf_appended": t_extra_leaf,
    "T14_tail_truncated_consistently": t_truncate_tail,
    "I01_receipts_swapped_between_events": t_idem_swap_events,
    "I02_row_index_changed": t_idem_row_index,
    "I03_receipt_verdict_changed": t_idem_receipt_verdict,
    "I04_receipt_emptied": t_idem_receipt_empty,
    "I05_row_names_missing_event": t_idem_dangling,
    "I06_two_keys_one_event": t_idem_duplicate,
    "I07_erased_record_kept_in_receipt": t_idem_erased_residue,
    "I08_rows_swapped_between_keys_OUT_OF_SCOPE": t_idem_rows_swapped,
}


def run(label: str, out: str) -> None:
    rng = random.Random(20261122)
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmp:
        clean_ok = 0
        clean_n = 60
        t0 = time.perf_counter()
        for i in range(clean_n):
            path = str(Path(tmp) / f"clean{i}.sqlite3")
            log, _, _ = build(path, rng)
            report = log.verify_log()
            clean_ok += bool(report["valid"])
            log.close()
        results["CLEAN_no_false_alarm"] = {"n": clean_n, "ok": clean_ok}
        for name, fn in CLASSES.items():
            detected = 0
            examples = []
            for i in range(K):
                path = str(Path(tmp) / f"{name}{i}.sqlite3")
                log, live, erased = build(path, rng)
                fn(path, rng, live, erased)
                try:
                    report = log.verify_log()
                    hit = not report["valid"]
                    if hit and len(examples) < 2:
                        examples.append(report["problems"][:2])
                except Exception as exc:  # raising also counts as detection
                    hit = True
                    examples.append([f"raised {type(exc).__name__}"])
                detected += hit
                log.close()
            results[name] = {"n": K, "detected": detected, "examples": examples}
        results["_seconds"] = round(time.perf_counter() - t0, 2)
    Path(out).write_text(
        json.dumps({"label": label, "results": results}, indent=1, ensure_ascii=False)
    )
    for k, v in results.items():
        if k.startswith("_"):
            continue
        print(f"{label:6} {k:38} {v.get('detected', v.get('ok'))}/{v['n']}")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
