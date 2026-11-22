"""Generate notes signed and cosigned by the Python implementation for the Go cross-verifier."""

import base64
import json
import sys

from ayorai_attractor.auditlog.cosignature import key_id, sign_cosignature
from ayorai_attractor.auditlog.merkle import leaf_hash, tree_root
from ayorai_attractor.auditlog.note import Checkpoint, NoteSigner
from tests.auditlog.test_witness_client import _pub


def vkey(name: str, seed: bytes) -> str:
    pub = _pub(seed)
    encoded = base64.b64encode(b"\x04" + pub).decode()
    return f"{name}+{key_id(name, pub).hex()}+{encoded}"


cases = []
for i, (origin, size, ts, cname) in enumerate(
    [
        ("example.com/verify-log", 0, 0, "witness.example/a"),
        ("example.com/verify-log", 1, 1_700_000_000, "witness.example/a"),
        ("ayorai.example/verify-log", 7, 1_800_000_000, "w.example/x-y_z"),
        ("ayorai.example/verify-log", 1000, (1 << 63) - 1, "oid/1.3.6.1.4.1.99999.1"),
        ("log.example", 33, 42, "witness.example/b"),
    ]
):
    signer = NoteSigner(origin, bytes([i + 1]) * 32)
    seed = bytes([100 + i]) * 32
    leaves = [leaf_hash(f"e{n}".encode()) for n in range(size)]
    note = signer.sign(Checkpoint(origin, size, tree_root(leaves)).body())
    body = note.split("\n\n", 1)[0] + "\n"
    cosigned = note + sign_cosignature(cname, seed, body, ts)
    base = {"log_vkey": signer.verifier_key, "cosigner_vkey": vkey(cname, seed)}
    cases.append({"id": f"valid-{i}", "note": cosigned, "expect": True, **base})
    if i == 1:
        tampered_body = cosigned.replace("\n1\n", "\n2\n", 1)
        cases.append({"id": "tampered-body", "note": tampered_body, "expect": False, **base})
        line = cosigned.rsplit("\n", 2)[-2]
        prefix, b64 = line.rsplit(" ", 1)
        raw = bytearray(base64.b64decode(b64))
        raw[-1] ^= 1
        bad = cosigned.replace(line, prefix + " " + base64.b64encode(bytes(raw)).decode())
        cases.append({"id": "tampered-cosignature", "note": bad, "expect": False, **base})
        raw = bytearray(base64.b64decode(b64))
        raw[4 + 7] ^= 1
        bad_ts = cosigned.replace(line, prefix + " " + base64.b64encode(bytes(raw)).decode())
        cases.append({"id": "tampered-timestamp", "note": bad_ts, "expect": False, **base})
        other = {**base, "cosigner_vkey": vkey(cname, bytes([200]) * 32)}
        cases.append({"id": "other-cosigner-key", "note": cosigned, "expect": False, **other})
for case in cases:
    sys.stdout.write(json.dumps(case) + "\n")
