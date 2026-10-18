"""ADR-010 phase 1 — salted commitments against independently computed vectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ayorai_attractor.auditlog import commitment

VECTORS = json.loads(
    (Path(__file__).parent / "vectors" / "commitment-v1.json").read_text(encoding="utf-8")
)


def test_domain_label_is_frozen() -> None:
    assert commitment.DOMAIN_LABEL.hex() == VECTORS["domain_label_hex"]


@pytest.mark.parametrize("vector", VECTORS["vectors"])
def test_commitment_matches_independent_vector(vector: dict[str, object]) -> None:
    salt = bytes.fromhex(str(vector["salt_hex"]))
    record = vector["record"]
    assert isinstance(record, dict)
    expected = bytes.fromhex(str(vector["commitment_hex"]))
    assert commitment.commit(record, salt) == expected
    assert commitment.verify_commitment(expected, record, salt)


def test_key_order_does_not_change_the_commitment() -> None:
    salt = bytes(range(32))
    a = {"verdict": "SUPPORTED", "decision_state": "DECIDED"}
    b = {"decision_state": "DECIDED", "verdict": "SUPPORTED"}
    assert commitment.commit(a, salt) == commitment.commit(b, salt)


def test_any_change_to_record_or_salt_breaks_verification() -> None:
    vector = VECTORS["vectors"][0]
    salt = bytes.fromhex(vector["salt_hex"])
    record = dict(vector["record"])
    value = commitment.commit(record, salt)
    for key in record:
        changed = {**record, key: str(record[key]) + "x"}
        assert not commitment.verify_commitment(value, changed, salt)
    assert not commitment.verify_commitment(value, {**record, "extra": 1}, salt)
    assert not commitment.verify_commitment(value, record, bytes(32))
    assert not commitment.verify_commitment(value[:-1] + bytes([value[-1] ^ 1]), record, salt)


def test_same_record_with_fresh_salts_is_unlinkable() -> None:
    record = {"verdict": "REFUTED"}
    first = commitment.commit(record, commitment.new_salt())
    second = commitment.commit(record, commitment.new_salt())
    assert first != second
    assert len(commitment.new_salt()) == commitment.SALT_SIZE == 32


@pytest.mark.parametrize(
    ("record", "salt", "message"),
    [
        ({"a": 1}, b"short", "32 bytes"),
        ({}, bytes(32), "non-empty"),
        ({1: "a"}, bytes(32), "strings"),
        ({"a": 2**60}, bytes(32), "RFC 8785"),
        ({"a": float("nan")}, bytes(32), "RFC 8785"),
        ({"a": object()}, bytes(32), "RFC 8785"),
    ],
)
def test_invalid_inputs_are_rejected(
    record: dict[object, object], salt: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        commitment.commit(record, salt)  # type: ignore[arg-type]
    assert not commitment.verify_commitment(bytes(32), record, salt)  # type: ignore[arg-type]


def test_verify_rejects_malformed_commitment() -> None:
    assert not commitment.verify_commitment(b"short", {"a": 1}, bytes(32))


def test_library_does_not_depend_on_the_judge_or_api() -> None:
    source_dir = Path(commitment.__file__).parent
    for path in source_dir.glob("*.py"):
        imports = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith(("import ", "from "))
        ]
        assert not [line for line in imports if "verification" in line or ".api" in line]
