"""r2-v3 audit replay digests bind every persisted field of a trace.

Threat model: the digest detects accidental corruption and edits made without
recomputing it (for example a direct UPDATE of one column). It is an unkeyed
SHA-256, so it does NOT detect an attacker with write access who recomputes it;
that needs a keyed MAC or signatures held outside the database.
"""

from __future__ import annotations

import itertools
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import _R2_V3_FIELDS, AuditTraceStore, _r2_v3_events
from ayorai_attractor.models import SearchResponse
from ayorai_attractor.replay import ReplayBundle

EDITS = {
    "legacy_verification": "'verified'",
    "verification": "'verified'",
    "operation_status": "'failed'",
    "evidence_count": "evidence_count + 1",
    "independent_evidence_count": "independent_evidence_count + 1",
    "verified_evidence_count": "verified_evidence_count + 1",
    "failure_count": "failure_count + 1",
    "finding_count": "0",
    "schema_version": "schema_version + 1",
}


def _store(tmp_path: Path) -> tuple[AuditTraceStore, Path]:
    path = tmp_path / "audit.sqlite3"
    return AuditTraceStore(str(path)), path


def _record(store: AuditTraceStore, trace_id: str = "tr_v3") -> None:
    response = SearchResponse.model_validate(
        {
            "query": "q",
            "mode": "balanced",
            "answer": "a",
            "verification": None,
            "verdict_authority": "not_adjudicated",
            "formal_verification_endpoint": "/v1/verify",
            "operation_status": "completed",
            "confidence": None,
            "evidence": [],
            "failures": [],
            "agents_used": [],
            "trace_id": trace_id,
        }
    )
    store.record(response, AuditReport.from_response(response))


def _edit(path: Path, assignments: dict[str, str], trace_id: str = "tr_v3") -> None:
    sql = ", ".join(f"{column} = {value}" for column, value in assignments.items())
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            f"UPDATE audit_traces SET {sql} WHERE trace_id = ?",  # noqa: S608
            (trace_id,),
        )


def test_every_persisted_field_is_bound() -> None:
    assert set(EDITS) == set(_R2_V3_FIELDS)


def test_new_traces_are_r2_v3_and_valid(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    with store:
        _record(store)
        saved = store.get("tr_v3")
        assert saved is not None
        assert saved.replay_version == "r2-v3"
        assert saved.replay_integrity == "valid"


@pytest.mark.parametrize("column", sorted(EDITS))
def test_editing_any_single_field_is_detected(tmp_path: Path, column: str) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store)
        _edit(path, {column: EDITS[column]})
        assert store.verify("tr_v3") == "invalid"


@pytest.mark.parametrize("pair", list(itertools.combinations(sorted(EDITS), 2)))
def test_editing_any_pair_of_fields_is_detected(tmp_path: Path, pair: tuple[str, str]) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store)
        _edit(path, {column: EDITS[column] for column in pair})
        assert store.verify("tr_v3") == "invalid"


def test_editing_the_version_or_digest_is_detected(tmp_path: Path) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store)
        _edit(path, {"replay_version": "'r2-v2'"})
        assert store.verify("tr_v3") == "invalid"
        _edit(path, {"replay_version": "'r2-v3'"})
        assert store.verify("tr_v3") == "valid"
        _edit(path, {"replay_digest": "'0' || substr(replay_digest, 2)"})
        assert store.verify("tr_v3") == "invalid"
        _edit(path, {"replay_version": "'r9-unknown'"})
        assert store.verify("tr_v3") == "invalid"


def test_restoring_the_original_values_is_valid_again(tmp_path: Path) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store)
        _edit(path, {"operation_status": "'failed'"})
        assert store.verify("tr_v3") == "invalid"
        _edit(path, {"operation_status": "'completed'"})
        assert store.verify("tr_v3") == "valid"


def test_an_unkeyed_digest_does_not_authenticate_a_recomputed_record(tmp_path: Path) -> None:
    """Documents the limit: write access plus recomputation passes verification."""
    store, path = _store(tmp_path)
    with store:
        _record(store)
        with closing(sqlite3.connect(path)) as connection, connection:
            columns = ", ".join(_R2_V3_FIELDS)
            row = connection.execute(
                f"SELECT {columns} FROM audit_traces WHERE trace_id = 'tr_v3'"  # noqa: S608
            ).fetchone()
            fields = dict(zip(_R2_V3_FIELDS, row, strict=True))
            fields["finding_count"] = 0
            forged = ReplayBundle.build("tr_v3", _r2_v3_events(fields), version="r2-v3").digest
            connection.execute(
                "UPDATE audit_traces SET finding_count = 0, replay_digest = ? "
                "WHERE trace_id = 'tr_v3'",
                (forged,),
            )
        assert store.verify("tr_v3") == "valid"


def test_existing_r2_v2_traces_keep_their_original_verification(tmp_path: Path) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store, "tr_old")
    legacy = ReplayBundle.build(
        "tr_old",
        [
            {
                "event": "audit.completed",
                "verification": "not_adjudicated",
                "evidence_count": 0,
                "failure_count": 0,
            }
        ],
        version="r2-v2",
    ).digest
    _edit(path, {"replay_version": "'r2-v2'", "replay_digest": f"'{legacy}'"}, "tr_old")
    with AuditTraceStore(str(path)) as reopened:
        assert reopened.verify("tr_old") == "valid"
        _edit(path, {"evidence_count": "evidence_count + 1"}, "tr_old")
        assert reopened.verify("tr_old") == "invalid"


def test_an_unknown_version_is_invalid_even_with_a_matching_digest(tmp_path: Path) -> None:
    store, path = _store(tmp_path)
    with store:
        _record(store)
        with closing(sqlite3.connect(path)) as connection, connection:
            columns = ", ".join(_R2_V3_FIELDS)
            row = connection.execute(
                f"SELECT {columns} FROM audit_traces WHERE trace_id = 'tr_v3'"  # noqa: S608
            ).fetchone()
            fields = dict(zip(_R2_V3_FIELDS, row, strict=True))
            digest = ReplayBundle.build("tr_v3", _r2_v3_events(fields), version="r9-x").digest
            connection.execute(
                "UPDATE audit_traces SET replay_version = 'r9-x', replay_digest = ? "
                "WHERE trace_id = 'tr_v3'",
                (digest,),
            )
        assert store.verify("tr_v3") == "invalid"
