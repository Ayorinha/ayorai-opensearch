"""Interop: WitnessClient (this branch) against the torchwood v0.10.0 witness on loopback TLS.

TLS is verified against the witness's own self-signed certificate (no verification is
disabled). Usage: python -P interop.py <witness-binary> <workdir>
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

from ayorai_attractor.auditlog.cosignature import verify_cosignature
from ayorai_attractor.auditlog.merkle import consistency_proof, leaf_hash, tree_root
from ayorai_attractor.auditlog.note import Checkpoint, NoteSigner
from ayorai_attractor.auditlog.witness_client import (
    WitnessClient,
    WitnessConflict,
    WitnessError,
    WitnessIdentity,
)

ORIGIN = "interop.example/verify-log"
SIGNER = NoteSigner(ORIGIN, bytes(range(32)))
binary, work = sys.argv[1], Path(sys.argv[2])
work.mkdir(parents=True, exist_ok=True)
for name in ("url", "cert.pem", "witness_vkey", "w.db", "w.db-wal", "w.db-shm"):
    (work / name).unlink(missing_ok=True)

results: list[dict[str, object]] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)[:200]})
    print(("PASS " if ok else "FAIL ") + name, detail)


def leaves(n: int) -> list[bytes]:
    return [f"event-{i}".encode() for i in range(n)]


def note(n: int, items: list[bytes] | None = None) -> str:
    items = leaves(n) if items is None else items
    return SIGNER.sign(
        Checkpoint(ORIGIN, len(items), tree_root([leaf_hash(x) for x in items])).body()
    )


def proof(old: int, new: int) -> list[bytes]:
    return consistency_proof(old, [leaf_hash(x) for x in leaves(new)])


proc = subprocess.Popen(
    [binary, str(work / "w.db"), ORIGIN, SIGNER.verifier_key, str(work)],
    stderr=open(work / "witness.log", "w"),
)
try:
    for _ in range(100):
        if (work / "url").exists() and (work / "witness_vkey").exists():
            break
        time.sleep(0.1)
    url = (work / "url").read_text()
    vkey = (work / "witness_vkey").read_text().strip()
    name, _, rest = vkey.partition("+")
    raw = base64.b64decode(rest.partition("+")[2])
    check("witness verifier key is C2SP type 0x04 Ed25519", raw[0] == 0x04 and len(raw) == 33, vkey)
    identity = WitnessIdentity(name, raw[1:])
    http = httpx.Client(verify=str(work / "cert.pem"), timeout=10)

    def client() -> WitnessClient:
        return WitnessClient(url, SIGNER.verifier_key, identity, client=http)

    c = client()
    first = c.submit(note(1), [])
    check(
        "S1 first contact (old 0, size 1) cosigned",
        verify_cosignature(first, name, raw[1:], now=int(time.time())),
    )
    third = c.submit(note(3), proof(1, 3))
    check(
        "S2 progression 1->3 with consistency proof cosigned",
        verify_cosignature(third, name, raw[1:], now=int(time.time())),
    )
    again = c.submit(note(3), [])
    check(
        "S3 repetition of size 3 (old 3, empty proof) cosigned",
        verify_cosignature(again, name, raw[1:], now=int(time.time())),
    )
    gap = c.submit(note(9), proof(3, 9))
    check("S4 gap 3->9 cosigned", verify_cosignature(gap, name, raw[1:], now=int(time.time())))

    fresh = client()
    try:
        fresh.submit(note(10), [])
        check("S5 stale client gets 409 with witness size", False, "accepted")
    except WitnessConflict as exc:
        check(
            "S5 stale client gets 409 with witness size 9", exc.witness_size == 9, exc.witness_size
        )
        check("S5 409 does not advance local state", fresh.last_checkpoint is None)

    resumed = fresh.submit(note(10), proof(9, 10), previous_checkpoint=gap)
    check(
        "S6 resume from witness checkpoint 9->10 cosigned",
        verify_cosignature(resumed, name, raw[1:], now=int(time.time())),
    )

    target = url.rstrip("/") + "/add-checkpoint"

    def raw_post(body: str) -> httpx.Response:
        return http.post(target, content=body.encode())

    r = raw_post(f"10\n\n{note(11)}")
    check(
        "S7 legacy first line without 'old ' is rejected (400)", r.status_code == 400, r.status_code
    )
    r = raw_post(
        "old 10\n"
        + "".join(base64.b64encode(bytes(32)).decode() + "\n" for _ in range(64))
        + "\n"
        + note(11)
    )
    check("S8 64 proof lines rejected (400)", r.status_code == 400, r.status_code)
    forked = note(11, [b"fork-" + bytes([i]) for i in range(11)])
    bad = consistency_proof(10, [leaf_hash(b"fork-" + bytes([i])) for i in range(11)])
    r = raw_post(
        "old 10\n" + "".join(base64.b64encode(x).decode() + "\n" for x in bad) + "\n" + forked
    )
    check("S9 split-view checkpoint rejected (422)", r.status_code == 422, r.status_code)
    try:
        fresh.submit(forked, bad)
        check("S9b client refuses the split view locally", False, "sent")
    except WitnessConflict:
        check("S9b client refuses the split view locally", False, "409")
    except WitnessError as exc:
        check("S9b client refuses the split view locally", "not consistent" in str(exc), exc)
    other = NoteSigner(ORIGIN, bytes(32)).sign(Checkpoint(ORIGIN, 11, bytes(32)).body())
    r = raw_post(f"old 10\n\n{other}")
    check(
        "S10 checkpoint signed by an unknown key rejected (403)",
        r.status_code == 403,
        r.status_code,
    )
    r = raw_post(f"old 3\n\n{note(11)}")
    check(
        "S11 wrong old size gives 409 text/x.tlog.size '10\\n'",
        r.status_code == 409
        and r.headers.get("content-type", "").startswith("text/x.tlog.size")
        and r.text == "10\n",
        (r.status_code, r.headers.get("content-type"), r.text),
    )
finally:
    proc.terminate()
    proc.wait(timeout=10)

(work / "interop.json").write_text(json.dumps(results, indent=1))
passed = sum(r["ok"] for r in results)
print(f"{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
