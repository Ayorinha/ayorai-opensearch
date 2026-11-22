"""C2SP tlog-witness HTTP client with monotonic local checkpoint state."""
from __future__ import annotations

import base64
import threading
from dataclasses import dataclass

import httpx

from ayorai_attractor.auditlog.cosignature import verify_cosignature
from ayorai_attractor.auditlog.merkle import verify_consistency
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
        if not self.name or len(self.name.encode("utf-8")) > 255:
            raise ValueError("invalid witness name")
        if not isinstance(self.public_key, bytes) or len(self.public_key) != 32:
            raise ValueError("witness Ed25519 public key must be 32 bytes")


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
        if not submission_url.startswith(("https://", "http://")):
            raise ValueError("submission_url must be HTTP(S)")
        self.submission_url = submission_url.rstrip("/") + "/add-checkpoint"
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
        consistency_proof: list[bytes] | tuple[bytes, ...],
        *,
        previous_checkpoint: str | None = None,
    ) -> str:
        """Submit a checkpoint; return it with a verified witness signature.

        For first contact, omit previous_checkpoint and use an empty proof.
        The witness's persisted state remains authoritative.
        """
        with self._lock:
            previous = self._last_checkpoint if previous_checkpoint is None else previous_checkpoint
            body = verify_note(checkpoint_note, self.log_verifier_key)
            current = parse_checkpoint(body) if body is not None else None
            if current is None:
                raise WitnessError("checkpoint is not signed by the configured log key")
            if previous is None:
                old_size = 0
                if consistency_proof:
                    raise WitnessError("the initial checkpoint must use an empty consistency proof")
            else:
                old_body = verify_note(previous, self.log_verifier_key)
                old = parse_checkpoint(old_body) if old_body is not None else None
                if old is None or old.origin != current.origin:
                    raise WitnessError("previous checkpoint is invalid or belongs to another log")
                if current.size < old.size:
                    raise WitnessError("checkpoint rollback refused")
                if current.size == old.size:
                    if current.root != old.root or consistency_proof:
                        raise WitnessError("same-size checkpoint does not match previous state")
                elif not verify_consistency(old.size, current.size, old.root, current.root, consistency_proof):
                    raise WitnessError("checkpoint is not consistent with previous state")
                old_size = old.size

            proof_lines = "".join(base64.b64encode(node).decode("ascii") + "\n" for node in consistency_proof)
            request_body = f"{old_size}\n{proof_lines}\n{checkpoint_note}"
            response = self._client.post(
                self.submission_url,
                content=request_body.encode("utf-8"),
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
            if response.status_code == 409:
                raise WitnessConflict("witness state conflicts with the submitted previous checkpoint")
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
