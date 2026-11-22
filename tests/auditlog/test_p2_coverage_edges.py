"""Boundary and failure-path tests for the P2 audit-log modules."""

from __future__ import annotations

import base64

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ayorai_attractor.auditlog.cosignature import (
    key_id,
    sign_cosignature,
    signed_message,
    verify_cosignature,
)
from ayorai_attractor.auditlog.merkle import empty_root
from ayorai_attractor.auditlog.note import Checkpoint, NoteSigner
from ayorai_attractor.auditlog.witness_client import (
    WitnessClient,
    WitnessError,
    WitnessIdentity,
)

LOG = "example.com/log"
LOG_SEED = bytes(range(32))
WITNESS = "witness.example"
WITNESS_SEED = bytes(range(32, 64))
PUB = (
    Ed25519PrivateKey.from_private_bytes(WITNESS_SEED)
    .public_key()
    .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
)
BODY = f"{LOG}\n0\n{base64.b64encode(empty_root()).decode()}\n"


@pytest.mark.parametrize("name", ["", "x" * 256, "white space", "bad+name", "bad\x01name", None])
def test_cosignature_rejects_invalid_names(name: object) -> None:
    with pytest.raises(ValueError):
        key_id(name, PUB)  # type: ignore[arg-type]


@pytest.mark.parametrize("public_key", [b"", bytes(31), bytearray(32), None])
def test_cosignature_rejects_invalid_public_key(public_key: object) -> None:
    with pytest.raises(ValueError):
        key_id(WITNESS, public_key)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("body", "timestamp"),
    [(BODY[:-1], 1), (BODY, -1), (BODY, True), (BODY, 1 << 64), (None, 1)],
)
def test_cosignature_rejects_invalid_message_inputs(body: object, timestamp: object) -> None:
    with pytest.raises(ValueError):
        signed_message(body, timestamp)  # type: ignore[arg-type]


@pytest.mark.parametrize("seed", [b"", bytes(31), bytearray(32), None])
def test_cosignature_rejects_invalid_private_seed(seed: object) -> None:
    with pytest.raises(ValueError):
        sign_cosignature(WITNESS, seed, BODY, 1)  # type: ignore[arg-type]


def test_cosignature_default_timestamp_and_malformed_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ayorai_attractor.auditlog.cosignature as module

    monkeypatch.setattr(module.time, "time", lambda: 1234)
    line = sign_cosignature(WITNESS, WITNESS_SEED, BODY)
    valid = BODY + "\n" + line
    assert verify_cosignature(valid, WITNESS, PUB, now=1234)
    with_unrelated_line = BODY + "\\n" + "ordinary text\\n" + line
    assert verify_cosignature(with_unrelated_line, WITNESS, PUB, now=1234)
    for note in (
        None,
        BODY,
        BODY + "\n" + line.rstrip("\n"),
        BODY + "\n— other AA==\n",
    ):
        assert not verify_cosignature(note, WITNESS, PUB, now=1234)  # type: ignore[arg-type]
    assert not verify_cosignature(valid, WITNESS, PUB, now=-1)
    assert not verify_cosignature(valid, WITNESS, PUB, max_future_skew=-1)
    assert not verify_cosignature(
        valid,
        WITNESS,
        PUB,
        max_future_skew=1.5,  # type: ignore[arg-type]
    )


def test_cosignature_skips_malformed_and_noncanonical_lines() -> None:
    good = sign_cosignature(WITNESS, WITNESS_SEED, BODY, 100)
    canonical = base64.b64encode(bytes(76)).decode("ascii")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    last_index = alphabet.index(canonical[-3])
    noncanonical = canonical[:-3] + alphabet[(last_index & ~15) | 1] + "=="
    assert base64.b64decode(noncanonical, validate=True) == bytes(76)
    malformed = (
        "— witness.example !!!\\n"
        "— witness.example AA==\\n"
        + "— witness.example " + noncanonical + "\\n"
    )
    assert verify_cosignature(BODY + "\n" + malformed + good, WITNESS, PUB, now=100)


@pytest.mark.parametrize(
    "proof",
    [
        "not-a-sequence",
        b"not-a-sequence",
        bytearray(b"x"),
        None,
        7,
        [bytearray(32)],
        [object()],
        [b"x" * 31],
        ["!!!!"],
    ],
)
def test_witness_rejects_malformed_proof_nodes(proof: object) -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    client = WitnessClient(
        "https://witness.example/submit",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError):
        client.submit(note, proof)  # type: ignore[arg-type]
    client.close()


@pytest.mark.parametrize("name", [None, 7, "", "white space"])
def test_witness_identity_rejects_invalid_name_types_and_values(name: object) -> None:
    with pytest.raises(ValueError):
        WitnessIdentity(name, PUB)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "url",
    [
        "http://witness.example",
        "https://witness.example/path?q=1",
        "https://witness.example/path#frag",
        "https://user:pass@witness.example/path",
    ],
)
def test_witness_rejects_insecure_or_ambiguous_urls(url: str) -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    with pytest.raises(ValueError):
        WitnessClient(url, signer.verifier_key, WitnessIdentity(WITNESS, PUB))


@pytest.mark.parametrize(
    "timeout",
    [0, -1, True, float("nan"), float("inf"), "5", pytest.param(10**1000, id="integer-overflow")],
)
def test_witness_rejects_invalid_timeouts(timeout: object) -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    with pytest.raises(ValueError):
        WitnessClient(
            "https://witness.example",
            signer.verifier_key,
            WitnessIdentity(WITNESS, PUB),
            timeout=timeout,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("status", [201, 400, 500])
def test_witness_rejects_non_200_status(status: int) -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
        client=http,
    )
    with pytest.raises(WitnessError, match=f"HTTP {status}"):
        client.submit(note, [])
    assert client.last_checkpoint is None
    http.close()


@pytest.mark.parametrize("response_text", ["", "incomplete", "— wrong AA==\n"])
def test_witness_rejects_incomplete_or_invalid_signature_response(
    response_text: str,
) -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=response_text)))
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
        client=http,
    )
    with pytest.raises(WitnessError):
        client.submit(note, [])
    assert client.last_checkpoint is None
    http.close()


def test_witness_wraps_transport_errors_without_advancing_state() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())

    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    http = httpx.Client(transport=httpx.MockTransport(fail))
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
        client=http,
    )
    with pytest.raises(WitnessError, match="request failed"):
        client.submit(note, [])
    assert client.last_checkpoint is None
    http.close()


def test_witness_rejects_invalid_previous_checkpoint_and_rollback() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
        client=http,
    )
    with pytest.raises(WitnessError, match="previous checkpoint"):
        client.submit(note, [], previous_checkpoint="invalid")
    previous = signer.sign(Checkpoint(LOG, 1, bytes(32)).body())
    with pytest.raises(WitnessError, match="rollback"):
        client.submit(note, [], previous_checkpoint=previous)
    http.close()


def test_witness_close_only_closes_owned_http_client() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    owned = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    owned_http = owned._client
    owned.close()
    assert owned_http.is_closed

    supplied_http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    supplied = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
        client=supplied_http,
    )
    supplied.close()
    assert not supplied_http.is_closed
    supplied_http.close()



@pytest.mark.parametrize("public_key", [b"", bytes(31), bytearray(32), None])
def test_witness_identity_rejects_invalid_public_keys(public_key: object) -> None:
    with pytest.raises(ValueError, match="public key"):
        WitnessIdentity(WITNESS, public_key)  # type: ignore[arg-type]


def test_witness_rejects_noncanonical_base64_proof_before_network_call() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    canonical = base64.b64encode(bytes(32)).decode("ascii")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    last_index = alphabet.index(canonical[-2])
    noncanonical = canonical[:-2] + alphabet[(last_index & ~3) | 1] + "="
    assert base64.b64decode(noncanonical, validate=True) == bytes(32)
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="non-canonical"):
        client.submit(note, [noncanonical])
    assert client.last_checkpoint is None
    client.close()


def test_witness_rejects_unsigned_checkpoint_before_network_call() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="not signed"):
        client.submit("not a signed checkpoint", [])
    assert client.last_checkpoint is None
    client.close()


def test_witness_rejects_nonempty_initial_proof_before_network_call() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    note = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="initial checkpoint"):
        client.submit(note, [bytes(32)])
    assert client.last_checkpoint is None
    client.close()


def test_witness_rejects_previous_checkpoint_from_another_origin() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    current = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    previous = signer.sign(Checkpoint("other.example/log", 0, empty_root()).body())
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="previous checkpoint"):
        client.submit(current, [], previous_checkpoint=previous)
    client.close()


def test_witness_rejects_nonempty_root_for_previous_size_zero() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    current = signer.sign(Checkpoint(LOG, 0, empty_root()).body())
    previous = signer.sign(Checkpoint(LOG, 0, bytes(32)).body())
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="size-zero"):
        client.submit(current, [], previous_checkpoint=previous)
    client.close()


def test_witness_rejects_same_size_checkpoint_with_different_root() -> None:
    signer = NoteSigner(LOG, LOG_SEED)
    previous = signer.sign(Checkpoint(LOG, 1, bytes([1]) * 32).body())
    current = signer.sign(Checkpoint(LOG, 1, bytes([2]) * 32).body())
    client = WitnessClient(
        "https://witness.example",
        signer.verifier_key,
        WitnessIdentity(WITNESS, PUB),
    )
    with pytest.raises(WitnessError, match="same-size checkpoint"):
        client.submit(current, [], previous_checkpoint=previous)
    client.close()
