"""ADR-010 phases 2–3: signed checkpoints, verification-event log and /v1/verify recording."""

from __future__ import annotations

import base64
import copy
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api import app as app_module
from ayorai_attractor.api import verify_log as verify_log_module
from ayorai_attractor.auditlog.merkle import verify_consistency
from ayorai_attractor.auditlog.note import NoteSigner, parse_checkpoint, verify_note
from ayorai_attractor.auditlog.store import (
    IdempotencyConflict,
    LogCorruption,
    VerificationEvent,
    VerificationLog,
    verify_receipt,
)

SEED = bytes(range(32))
ORIGIN = "attractor.example/verify-log"

# Public test vector of golang.org/x/mod/sumdb/note (the C2SP signed-note reference).
GO_SKEY = "PRIVATE+KEY+PeterNeumann+c74f20a3+AYEKFALVFGyNhPJEMzD1QIDr+Y7hfZx09iUvxdXHKDFz"
GO_VKEY = "PeterNeumann+c74f20a3+ARpc2QcUPDhMQegwxbzhKqiBfsVkmqq/LDE4izWy10TW"
GO_BODY = (
    "If you think cryptography is the answer to your problem,\n"
    "then you don't know what your problem is.\n"
)
GO_NOTE = (
    GO_BODY + "\n— PeterNeumann x08go/ZJkuBS9UG/SffcvIAQxVBtiFupLLr8pAcElZInNIuGU"
    "gYN1FFYC2pZSNXgKvqfqdngotpRZb6KE6RyyBwJnAM=\n"
)


def _event(n: int = 0, client: str = "client-a", verdict: str = "SUPPORTED") -> VerificationEvent:
    return VerificationEvent(
        input_sha256=f"{n:064x}",
        output_sha256=f"{n + 1:064x}",
        rules_sha256="a" * 64,
        decision_state="DECIDED",
        verdict=verdict,
        client=client,
        received_at="2026-11-21T00:00:00Z",
        software_id="ayorai-opensearch/test",
    )


@pytest.fixture
def log(tmp_path: Path) -> Any:
    with VerificationLog(str(tmp_path / "v.sqlite3"), NoteSigner(ORIGIN, SEED)) as store:
        yield store


# --- signed notes ---------------------------------------------------------------


def test_signed_note_matches_the_go_reference_vector() -> None:
    seed = base64.b64decode("+".join(GO_SKEY.split("+")[4:]))[1:]
    signer = NoteSigner("PeterNeumann", seed)
    assert signer.verifier_key == GO_VKEY
    assert signer.sign(GO_BODY) == GO_NOTE
    assert verify_note(GO_NOTE, GO_VKEY) == GO_BODY


def test_tampered_or_foreign_notes_are_rejected() -> None:
    assert verify_note(GO_NOTE.replace("cryptography", "Cryptography"), GO_VKEY) is None
    other = NoteSigner("PeterNeumann", bytes(32)).verifier_key
    assert verify_note(GO_NOTE, other) is None
    assert verify_note(GO_NOTE, "not-a-key") is None
    assert verify_note("no signature here\n", GO_VKEY) is None


def test_verifier_keys_with_plus_in_base64_parse() -> None:
    for counter in range(4096):
        signer = NoteSigner("log.example/x", counter.to_bytes(32, "big"))
        if "+" in signer.verifier_key.split("+", 2)[2]:
            assert verify_note(signer.sign("body\n"), signer.verifier_key) == "body\n"
            return
    pytest.fail("no key with '+' in its base64 found")


# --- the log --------------------------------------------------------------------


def test_receipt_verifies_offline_and_hides_the_verdict(log: VerificationLog) -> None:
    receipt = log.append(_event(1, verdict="REFUTED"))
    assert verify_receipt(receipt, log.verifier_key)
    leaf = json.loads(base64.b64decode(receipt["leaf"]))
    assert set(leaf) == {"schema", "rules_sha256", "software_id", "commitment"}
    assert "REFUTED" not in base64.b64decode(receipt["leaf"]).decode()
    assert receipt["record"]["verdict"] == "REFUTED"
    body = verify_note(receipt["checkpoint"], log.verifier_key)
    assert body is not None and parse_checkpoint(body) is not None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["record"].update(verdict="SUPPORTED"),
        lambda r: r["record"].update(input_sha256="f" * 64),
        lambda r: r.update(salt=base64.b64encode(bytes(32)).decode()),
        lambda r: r.update(index=r["index"] + 1),
        lambda r: r["inclusion_proof"].__setitem__(0, base64.b64encode(bytes(32)).decode()),
        lambda r: r.update(checkpoint=r["checkpoint"].replace("\n2\n", "\n3\n")),
        lambda r: r.update(receipt_version="other"),
        lambda r: r.pop("leaf"),
    ],
)
def test_any_change_to_a_receipt_is_rejected(log: VerificationLog, mutate: Any) -> None:
    log.append(_event(1))
    receipt = log.append(_event(2, verdict="REFUTED"))
    log.append(_event(3))
    tampered = copy.deepcopy(receipt)
    mutate(tampered)
    assert verify_receipt(receipt, log.verifier_key)
    assert not verify_receipt(tampered, log.verifier_key)


def test_receipt_does_not_verify_under_another_key(log: VerificationLog) -> None:
    receipt = log.append(_event(1))
    assert not verify_receipt(receipt, NoteSigner(ORIGIN, bytes(32)).verifier_key)


def test_old_receipts_stay_valid_and_checkpoints_are_consistent(log: VerificationLog) -> None:
    first = log.append(_event(1))
    for n in range(2, 12):
        log.append(_event(n))
    assert verify_receipt(first, log.verifier_key)
    old = parse_checkpoint(verify_note(first["checkpoint"], log.verifier_key) or "")
    new = parse_checkpoint(verify_note(log.latest_checkpoint(), log.verifier_key) or "")
    assert old is not None and new is not None
    proof = [base64.b64decode(node) for node in log.consistency(old.size)]
    assert verify_consistency(old.size, new.size, old.root, new.root, proof)


def test_idempotency_returns_the_same_receipt_and_detects_conflicts(log: VerificationLog) -> None:
    first = log.append(_event(1), idempotency_key="retry-1")
    again = log.append(_event(1), idempotency_key="retry-1")
    assert again == first
    assert log.size() == 1
    with pytest.raises(IdempotencyConflict):
        log.append(_event(2), idempotency_key="retry-1")
    # Keys are scoped per client: another client may use the same key.
    log.append(_event(2, client="client-b"), idempotency_key="retry-1")
    assert log.size() == 2
    with pytest.raises(ValueError, match="Idempotency-Key"):
        log.append(_event(3), idempotency_key="has space")


def test_restart_keeps_the_tree_and_receipts(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        receipt = store.append(_event(1))
        store.append(_event(2))
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        assert store.size() == 2
        assert store.verify_log()["valid"] is True
        assert verify_receipt(receipt, store.verifier_key)
        store.append(_event(3))
        assert store.verify_log()["valid"] is True


def test_a_database_cannot_be_reused_with_another_key_or_origin(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(1))
    with pytest.raises(LogCorruption):
        VerificationLog(path, NoteSigner(ORIGIN, bytes(32)))
    with pytest.raises(LogCorruption):
        VerificationLog(path, NoteSigner("other.example/log", SEED))


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE vlog_leaves SET leaf = X'00' WHERE idx = 1",
        "DELETE FROM vlog_leaves WHERE idx = 1",
        "UPDATE vlog_checkpoints SET note = replace(note, 'verify-log', 'verify-loq')",
        "DELETE FROM vlog_checkpoints WHERE size = 3",
    ],
)
def test_tampering_with_the_database_is_detected(tmp_path: Path, statement: str) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        for n in range(3):
            store.append(_event(n))
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement)
        connection.commit()
    try:
        with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
            report = store.verify_log()
    except LogCorruption:
        return  # detected when the tree is reloaded
    assert report["valid"] is False
    assert report["problems"]


def test_erasure_is_itself_logged_and_keeps_receipts_verifiable(log: VerificationLog) -> None:
    receipt = log.append(_event(1, client="titular-123"))
    log.append(_event(2))
    erasure_index = log.erase(receipt["index"], "2026-11-22T00:00:00Z")
    assert erasure_index == 2
    assert log.erase(receipt["index"], "2026-11-22T00:00:00Z") is None  # already erased
    assert log.erase(erasure_index, "2026-11-22T00:00:00Z") is None  # not an event
    assert log.erase(99, "2026-11-22T00:00:00Z") is None
    report = log.verify_log()
    assert report["valid"] is True and report["erased_records"] == 1 and report["size"] == 3
    assert verify_receipt(receipt, log.verifier_key)  # the client kept salt and record
    with closing(sqlite3.connect(log.path)) as connection:
        leaf = connection.execute("SELECT leaf FROM vlog_leaves WHERE idx = 2").fetchone()[0]
        record = connection.execute(
            "SELECT record, salt FROM vlog_records WHERE idx = 0"
        ).fetchone()
    fields = json.loads(bytes(leaf))
    assert fields == {
        "schema": "ayorai.verify-erasure.v1",
        "erased_index": 0,
        "erased_at": "2026-11-22T00:00:00Z",
        "reason": "data_subject_request",
    }
    assert "titular-123" not in bytes(leaf).decode()
    assert record == (None, None)


@pytest.mark.parametrize(
    "statement",
    [
        # erased outside the API: no erasure event in the tree
        "UPDATE vlog_records SET record = NULL, salt = NULL, erased_at = 'x' WHERE idx = 0",
        # record row removed entirely
        "DELETE FROM vlog_records WHERE idx = 0",
    ],
)
def test_silent_erasure_is_detected(tmp_path: Path, statement: str) -> None:
    path = str(tmp_path / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(1))
        store.append(_event(2))
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(statement)
        connection.commit()
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        report = store.verify_log()
    assert report["valid"] is False


def test_backup_restores_a_verifiable_log(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    copy = str(tmp_path / "backup" / "v.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        receipt = store.append(_event(1))
        store.append(_event(2))
        checkpoint = store.latest_checkpoint()
        assert store.backup(copy) == 2
        with pytest.raises(FileExistsError):
            store.backup(copy)
    with VerificationLog(copy, NoteSigner(ORIGIN, SEED)) as restored:
        assert restored.verify_log()["valid"] is True
        assert restored.latest_checkpoint() == checkpoint
        assert verify_receipt(receipt, restored.verifier_key)
        restored.append(_event(3))
        assert restored.verify_log()["valid"] is True


def test_two_writers_on_one_database_stay_consistent(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    first = VerificationLog(path, NoteSigner(ORIGIN, SEED))
    second = VerificationLog(path, NoteSigner(ORIGIN, SEED))
    try:
        receipts = []
        for n in range(6):
            writer = first if n % 2 == 0 else second
            receipts.append(writer.append(_event(n)))
        assert [receipt["index"] for receipt in receipts] == list(range(6))
        assert first.verify_log()["valid"] is True
        assert all(verify_receipt(receipt, first.verifier_key) for receipt in receipts)
    finally:
        first.close()
        second.close()


def test_failed_append_leaves_no_partial_event(
    log: VerificationLog, monkeypatch: pytest.MonkeyPatch
) -> None:
    log.append(_event(1))

    def broken_sign(body: str) -> str:
        raise RuntimeError("signing service down")

    monkeypatch.setattr(log.signer, "sign", broken_sign)
    with pytest.raises(RuntimeError):
        log.append(_event(2))
    monkeypatch.undo()
    assert log.size() == 1
    assert log.verify_log()["valid"] is True
    assert log.append(_event(2))["index"] == 1


# --- API ------------------------------------------------------------------------


def _r2a() -> dict[str, object]:
    return {
        "schema_version": "r2-a",
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": "Claim A",
        "atoms": [{"id": "a1", "text": "Claim A", "start_offset": 0, "end_offset": 7}],
        "evidence": [
            {
                "id": "e1",
                "claim_id": "c1",
                "source_id": "source-e1",
                "source_location": "document:1",
                "retrieved_at": "2026-10-11T12:00:00Z",
                "start_offset": 0,
                "end_offset": 7,
                "excerpt": "Claim A",
                "origin_id": "origin-e1",
            }
        ],
        "stances": [{"id": "s1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}],
        "source_texts": {"source-e1": "Claim A"},
    }


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    def configure(mode: str) -> TestClient:
        monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_MODE", mode)
        monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_KEY", SEED.hex())
        monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_ORIGIN", ORIGIN)
        monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_DB", str(tmp_path / "api-log.sqlite3"))
        verify_log_module.close_verify_log()
        return TestClient(app_module.app, raise_server_exceptions=False)

    yield configure
    verify_log_module.close_verify_log()


def test_off_mode_keeps_the_response_unchanged(api: Any) -> None:
    body = api("off").post("/v1/verify", json=_r2a()).json()
    assert "audit_status" not in body and "audit_receipt" not in body
    assert api("off").get("/v1/verify/log").status_code == 404


def test_local_mode_records_and_the_receipt_verifies_with_the_published_key(api: Any) -> None:
    client = api("local")
    response = client.post("/v1/verify", json=_r2a())
    assert response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "recorded"
    receipt = body["audit_receipt"]
    assert receipt["record"]["output_sha256"] == body["result"]["output_sha256"]
    assert receipt["record"]["verdict"] == body["result"]["verdict"]
    published = client.get("/v1/verify/log").json()
    assert published["origin"] == ORIGIN
    assert verify_receipt(receipt, published["verifier_key"])
    # The receipt is outside `result`: the Judge's hashes are those of the off mode.
    off = api("off").post("/v1/verify", json=_r2a()).json()
    assert off["result"] == body["result"]


def test_idempotency_key_over_http(api: Any) -> None:
    client = api("local")
    headers = {"Idempotency-Key": "req-001"}
    first = client.post("/v1/verify", json=_r2a(), headers=headers).json()["audit_receipt"]
    second = client.post("/v1/verify", json=_r2a(), headers=headers).json()["audit_receipt"]
    assert first == second
    other = _r2a()
    other["claim_text"] = "Claim B"
    other["atoms"] = [{"id": "a1", "text": "Claim B", "start_offset": 0, "end_offset": 7}]
    conflict = client.post("/v1/verify", json=other, headers=headers)
    assert conflict.status_code == 409
    invalid = client.post("/v1/verify", json=_r2a(), headers={"Idempotency-Key": "a b"})
    assert invalid.status_code == 422


def test_idempotent_retry_of_an_erased_event_is_409_over_http(api: Any) -> None:
    client = api("local")
    headers = {"Idempotency-Key": "req-erased"}
    first = client.post("/v1/verify", json=_r2a(), headers=headers).json()["audit_receipt"]
    store = verify_log_module.get_verify_log()
    store.erase(first["index"], "2026-11-22T00:00:00Z")
    size = store.size()
    retry = client.post("/v1/verify", json=_r2a(), headers=headers)
    assert retry.status_code == 409
    assert "erased" in retry.json()["detail"]
    assert store.size() == size


def test_idempotent_retry_with_a_tampered_receipt_is_never_served_over_http(
    api: Any, tmp_path: Path
) -> None:
    client = api("required")
    headers = {"Idempotency-Key": "req-tamper"}
    first = client.post("/v1/verify", json=_r2a(), headers=headers).json()["audit_receipt"]
    with closing(sqlite3.connect(str(tmp_path / "api-log.sqlite3"))) as connection:
        forged = dict(first, record=dict(first["record"], verdict="REFUTED"))
        connection.execute("UPDATE vlog_idempotency SET receipt = ?", (json.dumps(forged),))
        connection.commit()
    retry = client.post("/v1/verify", json=_r2a(), headers=headers)
    assert retry.status_code == 503
    assert "audit_receipt" not in retry.json()
    local = api("local").post("/v1/verify", json=_r2a(), headers=headers).json()
    assert local["audit_status"] == "not_recorded"
    assert "audit_receipt" not in local


def test_required_mode_fails_closed_and_local_mode_reports_not_recorded(
    api: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def failing(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("disk full")

    client = api("required")
    monkeypatch.setattr(verify_log_module.get_verify_log(), "append", failing)
    response = client.post("/v1/verify", json=_r2a())
    assert response.status_code == 503
    assert "result" not in response.json()

    client = api("local")
    monkeypatch.setattr(verify_log_module.get_verify_log(), "append", failing)
    body = client.post("/v1/verify", json=_r2a()).json()
    assert body["audit_status"] == "not_recorded"
    assert "audit_receipt" not in body
    assert body["result"]["verdict"] == "SUPPORTED"

    failures = [r for r in caplog.records if r.name == "ayorai_attractor.api.app"]
    assert [r.levelname for r in failures] == ["ERROR", "ERROR"]
    assert "mode=required" in failures[0].getMessage()
    assert "mode=local" in failures[1].getMessage()
    assert all("OperationalError" in r.getMessage() for r in failures)
    assert not any("disk full" in r.getMessage() for r in failures)


def test_r1a_is_never_recorded(api: Any) -> None:
    client = api("required")
    baseline = json.loads(
        (Path(__file__).parent / "fixtures" / "r1-a-response-baseline.json").read_text("utf-8")
    )
    response = client.post("/v1/verify", json=baseline["cases"][0]["request"])
    assert response.status_code == 200
    assert "audit_status" not in response.json()
    assert verify_log_module.get_verify_log().size() == 0


@pytest.mark.parametrize(
    ("key", "origin", "message"),
    [("", ORIGIN, "64 hex"), ("zz" * 32, ORIGIN, "64 hex"), (SEED.hex(), "", "ORIGIN")],
)
def test_startup_refuses_a_recording_mode_without_key_or_origin(
    monkeypatch: pytest.MonkeyPatch, key: str, origin: str, message: str
) -> None:
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_MODE", "required")
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_KEY", key)
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_ORIGIN", origin)
    with pytest.raises(ValueError, match=message):
        verify_log_module.validate_verify_log_configuration()
    monkeypatch.setenv("ATTRACTOR_VERIFY_LOG_MODE", "sometimes")
    with pytest.raises(ValueError, match="ATTRACTOR_VERIFY_LOG_MODE"):
        verify_log_module.verify_log_mode()


def test_seed_is_never_written_to_the_database(tmp_path: Path) -> None:
    path = tmp_path / "v.sqlite3"
    with VerificationLog(str(path), NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(1))
    assert SEED.hex().encode() not in path.read_bytes()
    assert SEED not in path.read_bytes()
    assert os.path.getsize(path) > 0


def test_external_checkpoints_detect_rollback_and_rewrites(tmp_path: Path) -> None:
    path = str(tmp_path / "v.sqlite3")
    old_copy = str(tmp_path / "old.sqlite3")
    with VerificationLog(path, NoteSigner(ORIGIN, SEED)) as store:
        store.append(_event(1))
        early = store.latest_checkpoint()
        store.backup(old_copy)
        store.append(_event(2))
        held_by_client = store.latest_checkpoint()
        assert store.matches_checkpoint(early) and store.matches_checkpoint(held_by_client)
        foreign = NoteSigner(ORIGIN, bytes(32)).sign(f"{ORIGIN}\n1\n{'A' * 43}=\n")
        assert not store.matches_checkpoint(foreign)
    # The operator restores the older copy: the client's newer checkpoint exposes it.
    with VerificationLog(old_copy, NoteSigner(ORIGIN, SEED)) as restored:
        assert restored.verify_log()["valid"] is True  # locally consistent
        assert restored.matches_checkpoint(early)
        assert not restored.matches_checkpoint(held_by_client)
        # Rewriting history after the rollback is exposed the same way.
        restored.append(_event(99))
        assert not restored.matches_checkpoint(held_by_client)


def test_concurrent_writers_produce_one_consistent_tree(tmp_path: Path) -> None:
    import threading

    path = str(tmp_path / "v.sqlite3")
    logs = [VerificationLog(path, NoteSigner(ORIGIN, SEED)) for _ in range(2)]
    receipts: list[dict[str, Any]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(offset: int) -> None:
        try:
            for n in range(10):
                receipt = logs[offset % 2].append(_event(offset * 100 + n))
                with lock:
                    receipts.append(receipt)
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(offset,)) for offset in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    try:
        assert errors == []
        assert sorted(receipt["index"] for receipt in receipts) == list(range(60))
        assert logs[0].verify_log()["valid"] is True
        assert all(verify_receipt(receipt, logs[0].verifier_key) for receipt in receipts)
    finally:
        for log in logs:
            log.close()


def test_idempotency_header_is_ignored_when_the_log_is_off(api: Any) -> None:
    # Contract: with the log off the header has no effect (Schemathesis sends any string).
    response = api("off").post("/v1/verify", json=_r2a(), headers={"Idempotency-Key": "x" * 500})
    assert response.status_code == 200
    assert "audit_status" not in response.json()
