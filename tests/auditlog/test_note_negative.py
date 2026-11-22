"""ADR-010: every rejection path of signed notes and checkpoints.

The accepting path is cross-checked against the Go reference
(``vectors/README.md``); these tests pin down what must be refused.
"""

from __future__ import annotations

import base64

import pytest

from ayorai_attractor.auditlog.note import (
    Checkpoint,
    NoteSigner,
    parse_checkpoint,
    verifier_key,
    verify_note,
)

NAME = "attractor.example/verify-log"
SIGNER = NoteSigner(NAME, bytes(range(32)))
BODY = Checkpoint(NAME, 3, bytes(32)).body()
NOTE = SIGNER.sign(BODY)
VKEY = SIGNER.verifier_key


# --- signer inputs -------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "has space", "plus+sign", "tab\tname", "é"])
def test_signer_rejects_invalid_key_names(name: str) -> None:
    with pytest.raises(ValueError, match="key name"):
        NoteSigner(name, bytes(32))


@pytest.mark.parametrize("seed", [b"", bytes(31), bytes(33)])
def test_signer_rejects_seeds_that_are_not_32_bytes(seed: bytes) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        NoteSigner(NAME, seed)


def test_signer_rejects_a_seed_that_is_not_bytes() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        NoteSigner(NAME, "0" * 32)  # type: ignore[arg-type]


@pytest.mark.parametrize("body", ["no newline", "a\n\nb\n", "\n\n"])
def test_signer_refuses_bodies_that_would_be_ambiguous(body: str) -> None:
    with pytest.raises(ValueError, match="note body"):
        SIGNER.sign(body)


# --- verifier keys -------------------------------------------------------------


def _vkey_parts() -> tuple[str, str, str]:
    name, key_hash, encoded = VKEY.split("+", 2)
    return name, key_hash, encoded


@pytest.mark.parametrize(
    "mutate",
    [
        lambda n, h, e: f"{n}+{h}",  # missing part
        lambda n, h, e: f"bad name+{h}+{e}",  # invalid name
        lambda n, h, e: f"{n}+zzzzzzzz+{e}",  # hash not hex
        lambda n, h, e: f"{n}+{h}00+{e}",  # hash of wrong length
        lambda n, h, e: f"{n}+{h}+{e[:-4]}",  # key truncated
        lambda n, h, e: f"{n}+{h}+!!!!",  # key not base64
        lambda n, h, e: f"{n}+{h}+" + base64.b64encode(b"\x02" + bytes(32)).decode(),  # not Ed25519
        lambda n, h, e: f"{n}+00000000+{e}",  # hash does not match name and key
        lambda n, h, e: f"other-name+{h}+{e}",  # hash does not match the name
    ],
)
def test_malformed_or_mismatched_verifier_keys_verify_nothing(mutate: object) -> None:
    vkey = mutate(*_vkey_parts())  # type: ignore[operator]
    assert verify_note(NOTE, vkey) is None


def test_verifier_key_round_trip() -> None:
    assert verifier_key(NAME, SIGNER.public_key) == VKEY
    assert verify_note(NOTE, VKEY) == BODY


# --- note structure ------------------------------------------------------------


@pytest.mark.parametrize(
    "note",
    [
        BODY,  # no signature block at all
        NOTE.rstrip("\n"),  # signature block without the final newline
        NOTE.replace("— ", "- ", 1),  # wrong signature-line prefix
        NOTE.replace("— ", "—", 1),  # prefix without the space
    ],
)
def test_structurally_invalid_notes_are_rejected(note: str) -> None:
    assert verify_note(note, VKEY) is None


def test_a_note_that_is_not_text_is_rejected() -> None:
    assert verify_note(NOTE.encode(), VKEY) is None  # type: ignore[arg-type]


def _signature_line() -> tuple[str, str]:
    body, signatures = NOTE.split("\n\n", 1)
    return body + "\n", signatures


@pytest.mark.parametrize(
    "line",
    [
        f"— {NAME} !!notbase64!!\n",  # signature not base64
        f"— {NAME} {base64.b64encode(bytes(10)).decode()}\n",  # signature of wrong length
        f"— {NAME} {base64.b64encode(bytes(68)).decode()}\n",  # wrong key hash
        f"— {NAME} extra field\n",  # three fields
    ],
)
def test_unusable_signature_lines_do_not_verify(line: str) -> None:
    body, _ = _signature_line()
    assert verify_note(f"{body}\n{line}", VKEY) is None


def test_a_valid_signature_among_unknown_ones_still_verifies() -> None:
    # Unknown signers (e.g. future witness cosignatures) are skipped, not fatal.
    body, signatures = _signature_line()
    foreign = NoteSigner("witness.example", bytes(32)).sign(body).split("\n\n", 1)[1]
    assert verify_note(f"{body}\n{foreign}{signatures}", VKEY) == body


def test_a_signature_over_another_body_does_not_verify() -> None:
    other = SIGNER.sign(Checkpoint(NAME, 4, bytes(32)).body())
    body, _ = _signature_line()
    forged = body + "\n" + other.split("\n\n", 1)[1]
    assert verify_note(forged, VKEY) is None


# --- checkpoint bodies ---------------------------------------------------------


ROOT = base64.b64encode(bytes(32)).decode()


@pytest.mark.parametrize(
    "body",
    [
        f"{NAME}\n3\n{ROOT}",  # no final newline
        f"{NAME}\n3\n{ROOT}\nextension\n",  # extension lines are not used by this log
        f"\n3\n{ROOT}\n",  # empty origin
        f"{NAME}\n03\n{ROOT}\n",  # leading zero
        f"{NAME}\n-1\n{ROOT}\n",  # negative size
        f"{NAME}\nthree\n{ROOT}\n",  # not a number
        f"{NAME}\n3\n!!!!\n",  # root not base64
        f"{NAME}\n3\n{base64.b64encode(bytes(31)).decode()}\n",  # root of wrong length
    ],
)
def test_malformed_checkpoint_bodies_are_rejected(body: str) -> None:
    assert parse_checkpoint(body) is None


def test_checkpoint_body_round_trip() -> None:
    parsed = parse_checkpoint(BODY)
    assert parsed == Checkpoint(NAME, 3, bytes(32))
    assert parsed is not None and parsed.body() == BODY
