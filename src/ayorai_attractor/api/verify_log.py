"""Configuration of the /v1/verify event log (ADR-010 phase 3, ADR-009 §15.1).

``ATTRACTOR_VERIFY_LOG_MODE``:

* ``off`` (default): nothing is recorded and the r2-a response is unchanged;
* ``local``: every r2-a decision is recorded; if recording fails, the verdict is
  still returned with ``audit_status = "not_recorded"``;
* ``required``: no verdict without a recorded event (owner decision 3): a
  recording failure returns HTTP 503 and the client may retry with the same
  ``Idempotency-Key``.

With ``local`` or ``required``, ``ATTRACTOR_VERIFY_LOG_KEY`` (Ed25519 seed, 64 hex
characters, from a secret manager) and ``ATTRACTOR_VERIFY_LOG_ORIGIN`` (the log's
name, printed in every checkpoint) are mandatory; the service refuses to start
without them. ``ATTRACTOR_VERIFY_LOG_DB`` defaults to ``.attractor/verify-log.sqlite3``.
"""

from __future__ import annotations

import os
import threading
from typing import Final

from ayorai_attractor.auditlog.note import NoteSigner
from ayorai_attractor.auditlog.store import VerificationLog

MODES: Final = ("off", "local", "required")
_lock = threading.Lock()
_log: VerificationLog | None = None


def verify_log_mode() -> str:
    mode = os.getenv("ATTRACTOR_VERIFY_LOG_MODE", "off").strip().lower() or "off"
    if mode not in MODES:
        raise ValueError(f"ATTRACTOR_VERIFY_LOG_MODE must be one of {', '.join(MODES)}")
    return mode


def _signer_from_env() -> NoteSigner:
    raw = os.getenv("ATTRACTOR_VERIFY_LOG_KEY", "").strip()
    origin = os.getenv("ATTRACTOR_VERIFY_LOG_ORIGIN", "").strip()
    if not origin:
        raise ValueError("ATTRACTOR_VERIFY_LOG_ORIGIN is required when the verify log is on")
    try:
        seed = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("ATTRACTOR_VERIFY_LOG_KEY must be 64 hex characters") from exc
    if len(seed) != 32:
        raise ValueError("ATTRACTOR_VERIFY_LOG_KEY must be 64 hex characters")
    return NoteSigner(origin, seed)


def validate_verify_log_configuration() -> None:
    """Fail closed at startup: a recording mode without its key never starts."""
    if verify_log_mode() != "off":
        _signer_from_env()


def get_verify_log() -> VerificationLog:
    global _log
    with _lock:
        if _log is None:
            path = os.getenv("ATTRACTOR_VERIFY_LOG_DB", ".attractor/verify-log.sqlite3")
            _log = VerificationLog(path, _signer_from_env())
        return _log


def close_verify_log() -> None:
    global _log
    with _lock:
        if _log is not None:
            _log.close()
            _log = None
