"""C2SP Ed25519 cosignature vectors and witness-client adversarial tests."""
from __future__ import annotations

import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ayorai_attractor.auditlog.cosignature import sign_cosignature, verify_cosignature
from ayorai_attractor.auditlog.merkle import consistency_proof, leaf_hash, tree_root, verify_consistency
from ayorai_attractor.auditlog.note import Checkpoint, NoteSigner, parse_checkpoint, verify_note
from ayorai_attractor.auditlog.witness_client import (
    WitnessClient,
    WitnessConflict,
    WitnessError,
    WitnessIdentity,
)

LOG_NAME = "example.com/verify-log"
LOG_SEED = bytes(range(32))
WITNESS_NAME = "witness.example/test"
WITNESS_SEED = bytes(range(32, 64))


def _pub(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _checkpoint(signer: NoteSigner, leaves: list[bytes]) -> str:
    return signer.sign(Checkpoint(signer.name, len(leaves), tree_root([leaf_hash(x) for x in leaves])).body())


def test_c2sp_v1_1_ed25519_vector_matches_exact_wire_bytes() -> None:
    vector_path = Path(__file__).parent / "vectors/c2sp-cosignature-ed25519-v1.1.0.json"
    vector = json.loads(vector_path.read_text(encoding="utf-8"))
    seed = bytes.fromhex(vector["seed_hex"])
    body = vector["checkpoint_body"]
    line = sign_cosignature(vector["cosigner_name"], seed, body, vector["timestamp"])
    assert line == vector["signature_line"]
    note = body + "\n" + "— log.example " + "AA==" + "\n" + line
    assert verify_cosignature(note, vector["cosigner_name"], bytes.fromhex(vector["public_key_hex"]), now=vector["timestamp"])


def test_cosignature_rejects_tampering_wrong_key_and_future_timestamp() -> None:
    body = f"{LOG_NAME}\n1\n{base64.b64encode(bytes(32)).decode()}\n"
    line = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 1_700_000_000)
    note = body + "\n" + "— log.example AA==\n" + line
    assert verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)
    assert not verify_cosignature(note.replace("1\n", "2\n", 1), WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)
    assert not verify_cosignature(note, WITNESS_NAME, _pub(bytes(reversed(WITNESS_SEED))), now=1_700_000_000)
    assert not verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_699_999_000)


def test_cosignature_ignores_unknown_cosigner_lines() -> None:
    body = f"{LOG_NAME}\n1\n{base64.b64encode(bytes(32)).decode()}\n"
    good = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 1_700_000_000)
    unknown = sign_cosignature("other.example/w", bytes(reversed(WITNESS_SEED)), body, 1_700_000_000)
    note = body + "\n" + unknown + good
    assert verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)


class _WitnessHarness:
    """Atomic in-memory witness used only by protocol tests."""

    def __init__(self) -> None:
        self.signer = NoteSigner(LOG_NAME, LOG_SEED)
        self.witness_seed = WITNESS_SEED
        self.witness_name = WITNESS_NAME
        self.latest: str | None = None
        self.lock = threading.Lock()
        self.requests = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        self.requests += 1
        header, separator, checkpoint_note = request.content.decode().partition("\n\n")
        if not separator:
            return httpx.Response(422)
        lines = header.splitlines()
        try:
            old_size = int(lines[0])
            proof = [base64.b64decode(line, validate=True) for line in lines[1:]]
        except (ValueError, IndexError):
            return httpx.Response(422)
        body = verify_note(checkpoint_note, self.signer.verifier_key)
        current = parse_checkpoint(body) if body is not None else None
        if current is None or current.origin != LOG_NAME:
            return httpx.Response(422)
        with self.lock:
            previous = parse_checkpoint(verify_note(self.latest, self.signer.verifier_key)) if self.latest else None
            if previous is None:
                if old_size != 0:
                    return httpx.Response(409)
            else:
                if old_size != previous.size or current.size < previous.size:
                    return httpx.Response(409)
                if current.size == previous.size:
                    if current.root != previous.root or proof:
                        return httpx.Response(422)
                elif not verify_consistency(previous.size, current.size, previous.root, current.root, proof):
                    return httpx.Response(422)
            self.latest = checkpoint_note
            line = sign_cosignature(self.witness_name, self.witness_seed, body, 1_700_000_000)
            return httpx.Response(200, text=line)


def _client(harness: _WitnessHarness) -> WitnessClient:
    transport = httpx.MockTransport(harness.handle)
    http = httpx.Client(transport=transport)
    return WitnessClient(
        "https://witness.example/submit",
        NoteSigner(LOG_NAME, LOG_SEED).verifier_key,
        WitnessIdentity(WITNESS_NAME, _pub(WITNESS_SEED)),
        client=http,
    )


def test_witness_client_accepts_cosigned_checkpoint_and_advances_state() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    note = _checkpoint(NoteSigner(LOG_NAME, LOG_SEED), [b"event-1"])
    result = client.submit(note, [])
    assert result == client.last_checkpoint
    assert verify_cosignature(result, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)


def test_witness_client_rejects_rollback_before_network_call() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    first = _checkpoint(signer, [b"one", b"two"])
    cosigned = client.submit(first, [])
    smaller = _checkpoint(signer, [b"one"])
    with pytest.raises(WitnessError, match="rollback"):
        client.submit(smaller, [], previous_checkpoint=cosigned)
    assert harness.requests == 1
    assert client.last_checkpoint == cosigned


def test_http_409_does_not_advance_local_checkpoint() -> None:
    harness = _WitnessHarness()
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    harness.latest = _checkpoint(signer, [b"already-seen"])
    client = _client(harness)
    candidate = _checkpoint(signer, [b"candidate"])
    with pytest.raises(WitnessConflict):
        client.submit(candidate, [])
    assert client.last_checkpoint is None


def test_split_view_consistency_proof_is_rejected() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    first_leaves = [b"original"]
    previous = _checkpoint(signer, first_leaves)
    client.submit(previous, [])
    forked_leaves = [b"forked", b"extra"]
    forked = _checkpoint(signer, forked_leaves)
    invalid_proof = consistency_proof(1, [leaf_hash(x) for x in forked_leaves])
    with pytest.raises(WitnessError, match="not consistent"):
        client.submit(forked, invalid_proof, previous_checkpoint=client.last_checkpoint)


def test_concurrent_submissions_cannot_roll_witness_state_back() -> None:
    harness = _WitnessHarness()
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    notes = [_checkpoint(signer, [b"one"]), _checkpoint(signer, [b"one", b"two"])]
    clients = [_client(harness), _client(harness)]

    def submit(index: int) -> str:
        try:
            return clients[index].submit(notes[index], [])
        except WitnessConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert results.count("conflict") == 1
    latest = parse_checkpoint(verify_note(harness.latest, signer.verifier_key))
    assert latest is not None and latest.size in (1, 2)
