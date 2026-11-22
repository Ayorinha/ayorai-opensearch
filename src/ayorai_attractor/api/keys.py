"""API-key registry with scopes, expiry and revocation without restart (ADR-012).

The registry is a JSON file (``ATTRACTOR_API_KEYS_FILE``) holding only keyed
digests, never keys::

    {"schema": "ayorai.api-keys.v1",
     "keys": [{"id": "ops-2026-11", "digest": "<64 hex>", "scopes": ["verify"],
               "expires_at": "2027-01-01T00:00:00Z", "revoked_at": null,
               "revoked_by": null}]}

The file is re-read when its modification time, size or inode changes, at most
once every ``ATTRACTOR_API_KEYS_RELOAD_SECONDS``. An invalid file at startup
stops the service; an invalid file later keeps the last valid registry and is
counted in ``attractor_api_keys_reload_failures_total`` (owner decision DEC-031).

Command line (the key is piped from the secret manager on standard input; it is
never generated, displayed or stored, only its digest)::

    python -c "import secrets; print(secrets.token_urlsafe(32))"   # into the secret manager
    <secret-manager read> | python -m ayorai_attractor.api.keys new --id ops --scope verify \
        --file keys.json [--expires 2027-01-01T00:00:00Z]
    python -m ayorai_attractor.api.keys revoke --file keys.json --id ops --by "Anderson"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

SCHEMA: Final = "ayorai.api-keys.v1"
SCOPES: Final = frozenset({"verify", "audit:write", "audit:read", "metrics"})
_KEY_FIELDS: Final = frozenset({"id", "digest", "scopes", "expires_at", "revoked_at", "revoked_by"})
_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_DEFAULT_RELOAD_SECONDS = 1.0

logger = logging.getLogger(__name__)

# Route -> scope (ADR-012 §3). Paths not listed need a valid key and no scope.
_EXACT_SCOPES: Final[dict[tuple[str, str], str]] = {
    ("POST", "/v1/check"): "verify",
    ("POST", "/v1/fields"): "verify",
    ("POST", "/v1/verify"): "verify",
    ("POST", "/v1/opensearch"): "verify",
    ("POST", "/v1/audit"): "audit:write",
    ("POST", "/v2/audit"): "audit:write",
    ("GET", "/v1/verify/log"): "audit:read",
    ("GET", "/metrics"): "metrics",
}
_AUDIT_TRACE = re.compile(r"/v1/audit/[^/]+")


def required_scope(method: str, path: str) -> str | None:
    """Scope a route needs, or ``None`` when any valid key is enough."""
    method = "GET" if method == "HEAD" else method
    normalized = path.rstrip("/") or "/"
    scope = _EXACT_SCOPES.get((method, normalized))
    if scope is not None:
        return scope
    if method == "GET" and _AUDIT_TRACE.fullmatch(normalized):
        return "audit:read"
    return None


class RegistryError(ValueError):
    """The key file is missing, unreadable or invalid (message never holds digests)."""


def _parse_time(value: object, field: str, index: int) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise RegistryError(f"keys[{index}].{field} must be null or YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise RegistryError(f"keys[{index}].{field} is not a valid date") from exc


@dataclass(frozen=True)
class KeyEntry:
    id: str
    digest: str
    scopes: frozenset[str]
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    def is_active(self, now: datetime) -> bool:
        if self.revoked_at is not None and self.revoked_at <= now:
            return False
        return self.expires_at is None or now < self.expires_at


def parse_registry(raw: bytes) -> tuple[KeyEntry, ...]:
    """Validate the whole file; raise :class:`RegistryError` on any problem."""
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"key file is not valid UTF-8 JSON ({type(exc).__name__})") from exc
    if not isinstance(document, dict) or set(document) != {"schema", "keys"}:
        raise RegistryError("key file must be an object with exactly 'schema' and 'keys'")
    if document["schema"] != SCHEMA:
        raise RegistryError(f"schema must be {SCHEMA!r}")
    keys = document["keys"]
    if not isinstance(keys, list):
        raise RegistryError("'keys' must be a list")
    entries: list[KeyEntry] = []
    seen_ids: set[str] = set()
    seen_digests: set[str] = set()
    for index, item in enumerate(keys):
        if not isinstance(item, dict) or set(item) != _KEY_FIELDS:
            raise RegistryError(f"keys[{index}] must have exactly {sorted(_KEY_FIELDS)}")
        key_id, digest, scopes = item["id"], item["digest"], item["scopes"]
        if not isinstance(key_id, str) or _ID.fullmatch(key_id) is None:
            raise RegistryError(f"keys[{index}].id is invalid")
        if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
            raise RegistryError(f"keys[{index}].digest must be 64 lowercase hex characters")
        if (
            not isinstance(scopes, list)
            or not scopes
            or not all(isinstance(scope, str) and scope in SCOPES for scope in scopes)
            or len(set(scopes)) != len(scopes)
        ):
            raise RegistryError(f"keys[{index}].scopes must be distinct values of {sorted(SCOPES)}")
        if key_id in seen_ids:
            raise RegistryError(f"keys[{index}].id is duplicated")
        if digest in seen_digests:
            raise RegistryError(f"keys[{index}].digest is duplicated")
        revoked_at = _parse_time(item["revoked_at"], "revoked_at", index)
        revoked_by = item["revoked_by"]
        if (revoked_at is None) != (revoked_by is None):
            raise RegistryError(f"keys[{index}]: revoked_at and revoked_by go together")
        if revoked_by is not None and (
            not isinstance(revoked_by, str) or not revoked_by.strip() or len(revoked_by) > 128
        ):
            raise RegistryError(f"keys[{index}].revoked_by must be 1-128 characters")
        seen_ids.add(key_id)
        seen_digests.add(digest)
        entries.append(
            KeyEntry(
                id=key_id,
                digest=digest,
                scopes=frozenset(scopes),
                expires_at=_parse_time(item["expires_at"], "expires_at", index),
                revoked_at=revoked_at,
                revoked_by=revoked_by,
            )
        )
    return tuple(entries)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError(f"duplicated field {key!r}")
        result[key] = value
    return result


def legacy_entries(digests: Sequence[str]) -> tuple[KeyEntry, ...]:
    """``ATTRACTOR_API_KEYS_HMAC_SHA256`` mode: every scope, no expiry."""
    return tuple(
        KeyEntry(id=f"legacy-{index}", digest=digest, scopes=SCOPES)
        for index, digest in enumerate(dict.fromkeys(digests))
    )


def reload_interval() -> float:
    raw = os.getenv("ATTRACTOR_API_KEYS_RELOAD_SECONDS", str(_DEFAULT_RELOAD_SECONDS)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("ATTRACTOR_API_KEYS_RELOAD_SECONDS must be a positive number") from exc
    if not 0 < value <= 3600:
        raise ValueError("ATTRACTOR_API_KEYS_RELOAD_SECONDS must be between 0 and 3600")
    return value


class KeyRegistry:
    """Last valid registry of one key file, re-read when the file changes."""

    def __init__(
        self,
        path: str,
        *,
        interval: float = _DEFAULT_RELOAD_SECONDS,
        on_failure: Callable[[], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.path = Path(path)
        self.interval = interval
        self._on_failure = on_failure
        self._clock = clock
        self._lock = threading.Lock()
        signature = self._signature()  # missing or unreadable file: fail at startup
        self.entries = self._read()
        self._signature_seen = signature
        self._checked = clock()
        logger.info("api key registry loaded: %d keys, %d active", *self._counts())

    def _signature(self) -> tuple[int, int, int]:
        try:
            stat = self.path.stat()
        except OSError as exc:
            raise RegistryError(f"key file cannot be read ({type(exc).__name__})") from exc
        return stat.st_mtime_ns, stat.st_size, stat.st_ino

    def _read(self) -> tuple[KeyEntry, ...]:
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise RegistryError(f"key file cannot be read ({type(exc).__name__})") from exc
        return parse_registry(raw)

    def _counts(self) -> tuple[int, int]:
        now = datetime.now(UTC)
        return len(self.entries), sum(entry.is_active(now) for entry in self.entries)

    def current(self) -> tuple[KeyEntry, ...]:
        now = self._clock()
        if now - self._checked < self.interval:
            return self.entries
        with self._lock:
            if now - self._checked < self.interval:
                return self.entries
            self._checked = now
            try:
                signature = self._signature()
                if signature == self._signature_seen:
                    return self.entries
                entries = self._read()
            except RegistryError as exc:
                # Keep the last valid registry (DEC-031); the alert makes it visible.
                logger.error("api key registry reload failed, keeping last valid: %s", exc)
                if self._on_failure is not None:
                    self._on_failure()
                return self.entries
            previous = {entry.id: entry for entry in self.entries}
            for entry in entries:
                old = previous.get(entry.id)
                if entry.revoked_at is not None and (old is None or old.revoked_at is None):
                    logger.warning(
                        "api key %s revoked by %s at %s",
                        entry.id,
                        entry.revoked_by,
                        entry.revoked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    )
            self.entries = entries
            self._signature_seen = signature
            logger.info("api key registry reloaded: %d keys, %d active", *self._counts())
            return self.entries


# --- command line -----------------------------------------------------------


def _pepper_from_env() -> bytes:
    raw = os.getenv("ATTRACTOR_API_KEY_PEPPER", "").strip()
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise SystemExit("ATTRACTOR_API_KEY_PEPPER must be set (64 lowercase hex characters)")
    return bytes.fromhex(raw)


def _now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_atomic(path: Path, document: dict[str, Any]) -> None:
    data = (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    parse_registry(data)  # never write a file the service would refuse
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _load_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    parse_registry(raw)  # RegistryError before anything is changed
    document: dict[str, Any] = json.loads(raw)
    return document


def _command_new(args: argparse.Namespace) -> int:
    from ayorai_attractor.api.auth import MIN_API_KEY_LENGTH, _api_key_digest

    if _ID.fullmatch(args.id) is None:
        raise SystemExit("--id must match [a-z0-9][a-z0-9._-]{0,63}")
    if args.expires is not None:
        _parse_time(args.expires, "expires_at", 0)
    # The tool never generates or displays a key: the key comes on a pipe from the
    # secret manager (it is a random token, not a password) and only its digest is stored.
    if sys.stdin.isatty():
        raise SystemExit("pipe the API key from the secret manager on standard input")
    key = sys.stdin.readline().strip()
    if len(key) < MIN_API_KEY_LENGTH:
        raise SystemExit(f"the API key must have at least {MIN_API_KEY_LENGTH} characters")
    entry = {
        "id": args.id,
        "digest": _api_key_digest(key, _pepper_from_env()),
        "scopes": sorted(set(args.scope)),
        "expires_at": args.expires,
        "revoked_at": None,
        "revoked_by": None,
    }
    path = Path(args.file)
    document: dict[str, Any] = (
        _load_document(path) if path.exists() else {"schema": SCHEMA, "keys": []}
    )
    document["keys"].append(entry)
    _write_atomic(path, document)
    print(f"entry {args.id} added to {path}", file=sys.stderr)
    return 0


def _command_revoke(args: argparse.Namespace) -> int:
    document = _load_document(Path(args.file))
    path = Path(args.file)
    for item in document["keys"]:
        if item["id"] == args.id:
            if item["revoked_at"] is not None:
                raise SystemExit(f"key {args.id} is already revoked")
            item["revoked_at"] = _now_text()
            item["revoked_by"] = args.by
            _write_atomic(path, document)
            print(f"key {args.id} revoked by {args.by}", file=sys.stderr)
            return 0
    raise SystemExit(f"no key with id {args.id}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ayorai_attractor.api.keys")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="registry entry for a key read from stdin")
    new.add_argument("--id", required=True)
    new.add_argument("--scope", action="append", choices=sorted(SCOPES), required=True)
    new.add_argument("--expires", help="UTC, YYYY-MM-DDTHH:MM:SSZ")
    new.add_argument("--file", required=True, help="key file to append the entry to (atomic)")
    revoke = commands.add_parser("revoke", help="mark a key as revoked in the key file")
    revoke.add_argument("--file", required=True)
    revoke.add_argument("--id", required=True)
    revoke.add_argument("--by", required=True, help="who revoked (recorded in the file)")
    args = parser.parse_args(argv)
    try:
        return _command_new(args) if args.command == "new" else _command_revoke(args)
    except RegistryError as exc:
        raise SystemExit(f"invalid key file: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
