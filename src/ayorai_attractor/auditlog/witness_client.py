"""C2SP tlog-witness HTTP client with monotonic local checkpoint state."""

from __future__ import annotations

import base64
import binascii
import math
import threading
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from ayorai_attractor.auditlog.cosignature import key_id, verify_cosignature
from ayorai_attractor.auditlog.merkle import empty_root, verify_consistency
from ayorai_attractor.auditlog.note import parse_checkpoint, verify_note


class WitnessError(RuntimeError):
    """A witness request failed or returned an invalid response."""


class WitnessConflict(WitnessError):
    """The witness has a newer or incompatible checkpoint (HTTP 409)."""


@dataclass(frozen=True)
class WitnessIdentity:
    name: str
    public_key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or len(self.name.encode("utf-8")) > 255:
            raise ValueError("invalid witness name")
        if not isinstance(self.public_key, bytes) or len(self.public_key) != 32:
            raise ValueError("witness Ed25519 public key must be 32 bytes")
        key_id(self.name, self.public_key)


def _decode_consistency_proof(proof: Sequence[bytes | str]) -> list[bytes]:
    """Accept raw Merkle nodes or the canonical base64 strings returned by VerificationLog."""
    if isinstance(proof, (str, bytes, bytearray)) or not isinstance(proof, Sequence):
        raise WitnessError("consistency proof must be a sequence of 32-byte nodes")
    decoded: list[bytes] = []
    try:
        for node in proof:
            if isinstance(node, bytes):
                raw = node
            elif isinstance(node, str):
                raw = base64.b64decode(node, validate=True)
                if base64.b64encode(raw).decode("ascii") != node:
                    raise WitnessError("consistency proof contains non-canonical base64")
            else:
                raise WitnessError("consistency proof nodes must be bytes or base64 strings")
            if len(raw) != 32:
                raise WitnessError("consistency proof nodes must be exactly 32 bytes")
            decoded.append(raw)
    except (ValueError, binascii.Error) as exc:
        raise WitnessError("consistency proof contains invalid base64") from exc
    return decoded


class WitnessClient:
    """Submit signed checkpoints and verify returned C2SP witness cosignatures."""

    def __init__(
        self,
        submission_url: str,
        log_verifier_key: str,
        witness: WitnessIdentity,
        *,
        client: httpx.Client | None = None,
        timeout: float = 5.0,
    ) -> None:
        parsed_url = httpx.URL(submission_url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.host
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("submission_url must be an HTTPS URL without query or fragment")
        if parsed_url.username or parsed_url.password:
            raise ValueError("submission_url must not contain embedded credentials")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        try:
            finite_timeout = math.isfinite(float(timeout))
        except (OverflowError, ValueError):
            finite_timeout = False
        if not finite_timeout:
            raise ValueError("timeout must be a finite positive number")
        self.submission_url = str(parsed_url).rstrip("/") + "/add-checkpoint"
        self.log_verifier_key = log_verifier_key
        self.witness = witness
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._lock = threading.RLock()
        self._last_checkpoint: str | None = None

    @property
    def last_checkpoint(self) -> str | None:
        with self._lock:
            return self._last_checkpoint

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def submit(
        self,
        checkpoint_note: str,
        consistency_proof: Sequence[bytes | str],
        *,
        previous_checkpoint: str | None = None,
    ) -> str:
        """Submit a checkpoint; return it with a verified witness signature.

        Proof nodes may be raw 32-byte hashes or canonical base64 strings. The
        latter matches VerificationLog.consistency() and the C2SP wire format.
        For first contact, omit previous_checkpoint and use an empty proof.
        The witness's persisted state remains authoritative.
        """
        with self._lock:
            proof_nodes = _decode_consistency_proof(consistency_proof)
            if (
                self._last_checkpoint is not None
                and previous_checkpoint is not None
                and previous_checkpoint != self._last_checkpoint
            ):
                raise WitnessError(
                    "explicit previous checkpoint cannot override locally observed state"
                )
            previous = self._last_checkpoint if previous_checkpoint is None else previous_checkpoint
            body = verify_note(checkpoint_note, self.log_verifier_key)
            current = parse_checkpoint(body) if body is not None else None
            if current is None:
                raise WitnessError("checkpoint is not signed by the configured log key")
            expected_origin = self.log_verifier_key.partition("+")[0]
            if current.origin != expected_origin:
                raise WitnessError("checkpoint origin does not match the configured log identity")
            if previous is None:
                old_size = 0
                if proof_nodes:
                    raise WitnessError("the initial checkpoint must use an empty consistency proof")
            else:
                old_body = verify_note(previous, self.log_verifier_key)
                old = parse_checkpoint(old_body) if old_body is not None else None
                if old is None or old.origin != current.origin:
                    raise WitnessError("previous checkpoint is invalid or belongs to another log")
                if current.size < old.size:
                    raise WitnessError("checkpoint rollback refused")
                if old.size == 0:
                    if old.root != empty_root() or proof_nodes:
                        raise WitnessError("size-zero checkpoint must use the empty root and proof")
                    if current.size == 0 and current.root != old.root:
                        raise WitnessError(
                            "same-size empty checkpoint does not match previous state"
                        )
                elif current.size == old.size:
                    if current.root != old.root or proof_nodes:
                        raise WitnessError("same-size checkpoint does not match previous state")
                elif not verify_consistency(
                    old.size, current.size, old.root, current.root, proof_nodes
                ):
                    raise WitnessError("checkpoint is not consistent with previous state")
                old_size = old.size

            proof_lines = "".join(
                base64.b64encode(node).decode("ascii") + "\n" for node in proof_nodes
            )
            request_body = f"{old_size}\n{proof_lines}\n{checkpoint_note}"
            try:
                response = self._client.post(
                    self.submission_url,
                    content=request_body.encode("utf-8"),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                )
            except httpx.HTTPError as exc:
                raise WitnessError("witness request failed") from exc
            if response.status_code == 409:
                raise WitnessConflict(
                    "witness state conflicts with the submitted previous checkpoint"
                )
            if response.status_code != 200:
                raise WitnessError(f"witness returned HTTP {response.status_code}")
            signatures = response.text
            if not signatures or not signatures.endswith("\n"):
                raise WitnessError("witness response contains no complete signature lines")
            cosigned = checkpoint_note + signatures
            if not verify_cosignature(cosigned, self.witness.name, self.witness.public_key):
                raise WitnessError("witness response has no valid C2SP Ed25519 cosignature")
            self._last_checkpoint = cosigned
            return cosigned
