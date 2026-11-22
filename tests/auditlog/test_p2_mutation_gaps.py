"""Tests for the test gaps found by mutation testing of the verify log (P2 closure).

Each test kills a mutant that survived the full suite: the code was right, but no
test would have noticed the change.
"""

from __future__ import annotations

import base64
import dataclasses
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import LogCorruption, VerificationLog, verify_receipt
from tests.test_verify_log import ORIGIN, SEED, _event


def _sql(path: str, statement: str) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement)
        connection.commit()


def test_missing_first_checkpoint_is_reported(tmp_path: Path) -> None:
    """Checkpoint 1 is required like any other: the check starts at size 1."""
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        for n in range(3):
            store.append(_event(n))
        _sql(path, "DELETE FROM vlog_checkpoints WHERE size = 1")
        report = store.verify_log()
        assert report["valid"] is False
        assert "checkpoint 1: missing" in report["problems"]


def test_bool_index_does_not_stand_for_index_1(tmp_path: Path) -> None:
    """``True == 1`` in Python; a receipt for leaf 1 with ``index: true`` must not verify."""
    with VerificationLog(str(tmp_path / "v.sqlite3"), NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0))
        receipt = store.append(_event(1))
        assert receipt["index"] == 1
        assert verify_receipt(receipt, store.verifier_key)
        assert not verify_receipt({**receipt, "index": True}, store.verifier_key)


@pytest.mark.parametrize("field", ["leaf", "salt", "inclusion_proof"])
def test_receipt_base64_with_characters_outside_the_alphabet_does_not_verify(
    tmp_path: Path, field: str
) -> None:
    """Lenient base64 would drop the stray characters and accept a malleated receipt."""
    with VerificationLog(str(tmp_path / "v.sqlite3"), NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0))
        receipt = store.append(_event(1))
        vkey = store.verifier_key
    assert receipt["inclusion_proof"], "leaf 1 of 2 has a one-node inclusion proof"
    if field == "inclusion_proof":
        malleated = {**receipt, field: ["!" + receipt[field][0]]}
    else:
        malleated = {**receipt, field: "!" + receipt[field]}
    # The stray character is ignored by a lenient decoder: the bytes are the same.
    original = receipt[field][0] if field == "inclusion_proof" else receipt[field]
    stray = malleated[field][0] if field == "inclusion_proof" else malleated[field]
    assert base64.b64decode(stray) == base64.b64decode(original)
    assert not verify_receipt(malleated, vkey)


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param("UPDATE vlog_leaves SET leaf = X'7b7d' WHERE idx = 1", id="stale-hash"),
        pytest.param("UPDATE vlog_leaves SET idx = 7 WHERE idx = 2", id="gap"),
    ],
)
def test_reopen_refuses_a_hash_mismatch_or_a_gap_alone(tmp_path: Path, statement: str) -> None:
    """Either condition alone is corruption; neither needs the other."""
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        for n in range(3):
            store.append(_event(n))
    _sql(path, statement)
    with pytest.raises(LogCorruption):
        VerificationLog(path, NoteSigner(ORIGIN, SEED))


def test_verification_event_is_immutable() -> None:
    event = _event(0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.verdict = "REFUTED"  # type: ignore[misc]


def test_log_creates_a_missing_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "v.sqlite3"
    with VerificationLog(str(path), NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(0))
    assert path.exists()


# --- witness client -----------------------------------------------------------------


def _identity_key() -> bytes:
    from tests.auditlog.test_witness_client import WITNESS_SEED, _pub

    return _pub(WITNESS_SEED)


def test_witness_name_of_255_bytes_is_accepted_and_256_refused() -> None:
    from ayorai_attractor.auditlog.witness_client import WitnessIdentity

    assert WitnessIdentity("w" * 255, _identity_key()).name == "w" * 255
    with pytest.raises(ValueError):
        WitnessIdentity("w" * 256, _identity_key())


def test_witness_identity_is_immutable() -> None:
    from ayorai_attractor.auditlog.witness_client import WitnessIdentity

    identity = WitnessIdentity("witness.example/w", _identity_key())
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity.name = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "url", ["https://user@witness.example/submit", "https://:secret@witness.example/submit"]
)
def test_submission_url_with_only_a_username_or_only_a_password_is_refused(url: str) -> None:
    from ayorai_attractor.auditlog.witness_client import WitnessClient, WitnessIdentity

    with pytest.raises(ValueError, match="credentials"):
        WitnessClient(
            url,
            NoteSigner(ORIGIN, SEED).verifier_key,
            WitnessIdentity("witness.example/w", _identity_key()),
        )


def test_sub_second_timeout_is_accepted() -> None:
    from ayorai_attractor.auditlog.witness_client import WitnessClient, WitnessIdentity

    client = WitnessClient(
        "https://witness.example/submit",
        NoteSigner(ORIGIN, SEED).verifier_key,
        WitnessIdentity("witness.example/w", _identity_key()),
        timeout=0.5,
    )
    client.close()


def test_cosignature_line_without_its_final_newline_is_refused() -> None:
    import httpx

    from ayorai_attractor.auditlog.cosignature import sign_cosignature
    from ayorai_attractor.auditlog.note import verify_note
    from ayorai_attractor.auditlog.witness_client import (
        WitnessClient,
        WitnessError,
        WitnessIdentity,
    )
    from tests.auditlog.test_witness_client import (
        LOG_NAME,
        LOG_SEED,
        WITNESS_NAME,
        WITNESS_SEED,
        _checkpoint,
        _pub,
    )

    signer = NoteSigner(LOG_NAME, LOG_SEED)
    note = _checkpoint(signer, [b"one"])
    body = verify_note(note, signer.verifier_key)
    assert body is not None
    line = sign_cosignature(WITNESS_NAME, WITNESS_SEED, body, 1_700_000_000)
    assert line.endswith("\n")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=line[:-1])

    client = WitnessClient(
        "https://witness.example/submit",
        signer.verifier_key,
        WitnessIdentity(WITNESS_NAME, _pub(WITNESS_SEED)),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WitnessError, match="no complete signature lines"):
        client.submit(note, [])
    assert client.last_checkpoint is None


# --- cosignature verification ---------------------------------------------------------

_COSIGNER = "witness.example/mutation"
_COSIGNER_SEED = bytes(range(64, 96))
_BODY = f"{ORIGIN}\n1\n{base64.b64encode(bytes(32)).decode()}\n"


def _cosigner_key() -> bytes:
    from tests.auditlog.test_witness_client import _pub

    return _pub(_COSIGNER_SEED)


def _cosigned(timestamp: int, *, before: str = "") -> str:
    from ayorai_attractor.auditlog.cosignature import sign_cosignature

    return _BODY + "\n" + before + sign_cosignature(_COSIGNER, _COSIGNER_SEED, _BODY, timestamp)


def test_default_future_skew_is_300_seconds() -> None:
    from ayorai_attractor.auditlog.cosignature import verify_cosignature

    now = 1_700_000_000
    assert verify_cosignature(_cosigned(now + 300), _COSIGNER, _cosigner_key(), now=now)
    assert not verify_cosignature(_cosigned(now + 301), _COSIGNER, _cosigner_key(), now=now)


@pytest.mark.parametrize(
    ("now", "valid"),
    [
        pytest.param(0, True, id="zero"),
        pytest.param((1 << 64) - 1, True, id="uint64-max"),
        pytest.param(-1, False, id="negative"),
        pytest.param(1 << 64, False, id="above-uint64"),
        pytest.param(True, False, id="bool"),
        pytest.param(0.0, False, id="float"),
    ],
)
def test_now_must_be_a_uint64_integer(now: object, valid: bool) -> None:
    from ayorai_attractor.auditlog.cosignature import verify_cosignature

    note = _cosigned(0)
    assert verify_cosignature(note, _COSIGNER, _cosigner_key(), now=now) is valid  # type: ignore[arg-type]


def test_signature_line_with_an_extra_field_is_ignored() -> None:
    from ayorai_attractor.auditlog.cosignature import verify_cosignature

    note = _cosigned(0)
    assert verify_cosignature(note, _COSIGNER, _cosigner_key(), now=0)
    assert not verify_cosignature(note[:-1] + " extra\n", _COSIGNER, _cosigner_key(), now=0)


def test_malformed_line_with_the_right_key_id_does_not_hide_a_valid_one() -> None:
    """A too-short payload with the right key ID is skipped, not fatal."""
    from ayorai_attractor.auditlog.cosignature import key_id, verify_cosignature

    short = key_id(_COSIGNER, _cosigner_key()) + bytes(8) + bytes(10)
    bad_line = f"— {_COSIGNER} {base64.b64encode(short).decode()}\n"
    assert verify_cosignature(_cosigned(0, before=bad_line), _COSIGNER, _cosigner_key(), now=0)
