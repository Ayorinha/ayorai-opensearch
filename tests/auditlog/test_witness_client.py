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

from ayorai_attractor.auditlog.cosignature import key_id, sign_cosignature, verify_cosignature
from ayorai_attractor.auditlog.merkle import (
    consistency_proof,
    empty_root,
    leaf_hash,
    tree_root,
    verify_consistency,
)
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
    return (
        Ed25519PrivateKey.from_private_bytes(seed)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def _checkpoint(signer: NoteSigner, leaves: list[bytes]) -> str:
    root = tree_root([leaf_hash(leaf) for leaf in leaves])
    checkpoint = Checkpoint(signer.name, len(leaves), root)
    return signer.sign(checkpoint.body())


def test_c2sp_v1_1_ed25519_vector_matches_exact_wire_bytes() -> None:
    vector_path = Path(__file__).parent / "vectors/c2sp-cosignature-ed25519-v1.1.0.json"
    vector = json.loads(vector_path.read_text(encoding="utf-8"))
    seed = bytes.fromhex(vector["seed_hex"])
    body = vector["checkpoint_body"]
    line = sign_cosignature(vector["cosigner_name"], seed, body, vector["timestamp"])
    assert line == vector["signature_line"]
    note = body + "\n" + "— log.example " + "AA==" + "\n" + line
    public_key = bytes.fromhex(vector["public_key_hex"])
    assert verify_cosignature(note, vector["cosigner_name"], public_key, now=vector["timestamp"])


def test_cosignature_rejects_tampering_wrong_key_and_future_timestamp() -> None:
    body = f"{LOG_NAME}\n1\n{base64.b64encode(bytes(32)).decode()}\n"
    line = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 1_700_000_000)
    note = body + "\n" + "— log.example AA==\n" + line
    assert verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)
    tampered = note.replace("1\n", "2\n", 1)
    assert not verify_cosignature(tampered, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)
    wrong_key = _pub(bytes(reversed(WITNESS_SEED)))
    assert not verify_cosignature(note, WITNESS_NAME, wrong_key, now=1_700_000_000)
    assert not verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_699_999_000)
    private_key = Ed25519PrivateKey.from_private_bytes(WITNESS_SEED)
    zero_message = f"cosignature/v1\ntime 0\n{body}".encode()
    zero_payload = key_id(WITNESS_NAME, _pub(WITNESS_SEED)) + bytes(8)
    zero_payload += private_key.sign(zero_message)
    zero_line = f"— {WITNESS_NAME} {base64.b64encode(zero_payload).decode('ascii')}\n"
    zero_note = body + "\n" + zero_line
    assert verify_cosignature(zero_note, WITNESS_NAME, _pub(WITNESS_SEED), now=1_700_000_000)
    assert sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 0) == zero_line


def test_cosignature_name_rejects_unicode_whitespace_and_accepts_uint64_timestamp() -> None:
    body = f"{LOG_NAME}\n1\n{base64.b64encode(bytes(32)).decode()}\n"
    with pytest.raises(ValueError, match="Unicode spaces"):
        sign_cosignature("witness example", WITNESS_SEED, body, 1)
    maximum = (1 << 64) - 1
    line = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, maximum)
    note = body + "\n" + line
    assert verify_cosignature(
        note, WITNESS_NAME, _pub(WITNESS_SEED), now=maximum, max_future_skew=0
    )
    assert not verify_cosignature(note, WITNESS_NAME, _pub(WITNESS_SEED), now=True)
    assert not verify_cosignature(
        note, WITNESS_NAME, _pub(WITNESS_SEED), now=maximum, max_future_skew=True
    )


def test_cosignature_ignores_unknown_cosigner_lines() -> None:
    body = f"{LOG_NAME}\n1\n{base64.b64encode(bytes(32)).decode()}\n"
    good = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 1_700_000_000)
    unknown_seed = bytes(reversed(WITNESS_SEED))
    unknown = sign_cosignature("other.example/w", unknown_seed, body, 1_700_000_000)
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
            previous = None
            if self.latest:
                previous_body = verify_note(self.latest, self.signer.verifier_key)
                previous = parse_checkpoint(previous_body) if previous_body is not None else None
            if previous is None:
                if old_size != 0:
                    return httpx.Response(409)
            else:
                if old_size != previous.size or current.size < previous.size:
                    return httpx.Response(409)
                if previous.size == 0:
                    if previous.root != empty_root() or proof:
                        return httpx.Response(422)
                    if current.size == 0 and current.root != previous.root:
                        return httpx.Response(422)
                elif current.size == previous.size:
                    if current.root != previous.root or proof:
                        return httpx.Response(422)
                elif not verify_consistency(
                    previous.size, current.size, previous.root, current.root, proof
                ):
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


def test_witness_client_advances_with_a_valid_consistency_proof() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    leaves = [b"one"]
    first = _checkpoint(signer, leaves)
    client.submit(first, [])
    grown = [*leaves, b"two"]
    second = _checkpoint(signer, grown)
    proof = [
        base64.b64encode(node).decode("ascii")
        for node in consistency_proof(1, [leaf_hash(leaf) for leaf in grown])
    ]
    result = client.submit(second, proof)
    checkpoint_body = verify_note(result, signer.verifier_key)
    parsed = parse_checkpoint(checkpoint_body) if checkpoint_body is not None else None
    assert parsed is not None and parsed.size == 2



def test_witness_client_rejects_malformed_base64_proof_before_network_call() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    first = _checkpoint(signer, [b"one"])
    client.submit(first, [])
    grown = _checkpoint(signer, [b"one", b"two"])
    with pytest.raises(WitnessError, match="invalid base64"):
        client.submit(grown, ["not-base64!"])
    assert harness.requests == 1
    assert client.last_checkpoint is not None


def test_witness_client_rejects_signed_checkpoint_with_wrong_origin() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    wrong_origin = signer.sign(Checkpoint("other.example/log", 0, tree_root([])).body())
    with pytest.raises(WitnessError, match="origin"):
        client.submit(wrong_origin, [])
    assert harness.requests == 0
    assert client.last_checkpoint is None


def test_witness_client_rejects_conflicting_empty_checkpoint() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    empty = signer.sign(Checkpoint(LOG_NAME, 0, empty_root()).body())
    client.submit(empty, [])
    conflicting = signer.sign(Checkpoint(LOG_NAME, 0, bytes(32)).body())
    with pytest.raises(WitnessError, match="same-size empty checkpoint"):
        client.submit(conflicting, [])
    assert harness.requests == 1


def test_witness_client_advances_from_a_signed_empty_checkpoint() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    empty = signer.sign(Checkpoint(LOG_NAME, 0, empty_root()).body())
    client.submit(empty, [])
    first = _checkpoint(signer, [b"first-event"])
    result = client.submit(first, [])
    parsed = parse_checkpoint(verify_note(result, signer.verifier_key))
    assert parsed is not None and parsed.size == 1
    assert harness.requests == 2


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


def test_explicit_previous_checkpoint_cannot_bypass_local_monotonic_state() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    signer = NoteSigner(LOG_NAME, LOG_SEED)
    first = _checkpoint(signer, [b"one"])
    client.submit(first, [])
    stale_previous = _checkpoint(signer, [])
    candidate = _checkpoint(signer, [b"one", b"two"])
    proof = consistency_proof(1, [leaf_hash(b"one"), leaf_hash(b"two")])
    with pytest.raises(WitnessError, match="cannot override locally observed state"):
        client.submit(candidate, proof, previous_checkpoint=stale_previous)
    assert harness.requests == 1
    assert client.last_checkpoint is not None


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
