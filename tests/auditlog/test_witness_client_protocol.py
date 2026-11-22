"""Witness client: proof-size limits, 409 handling and the checkpoint sequence.

Rules come from C2SP tlog-witness (editor's copy): the request is ``old <size>``,
at most 63 base64 proof lines, an empty line and the checkpoint; ``old 0`` means
the witness has no state for the log and takes an empty proof; a 409 carries the
witness's latest size as ``text/x.tlog.size``. Nothing here adds a rule of its own.
"""

from __future__ import annotations

import base64

import httpx
import pytest

from ayorai_attractor.auditlog.merkle import consistency_proof, empty_root, leaf_hash
from ayorai_attractor.auditlog.note import Checkpoint, NoteSigner, parse_checkpoint, verify_note
from ayorai_attractor.auditlog.witness_client import (
    WitnessClient,
    WitnessConflict,
    WitnessError,
    WitnessIdentity,
    _decode_consistency_proof,
)
from tests.auditlog.test_witness_client import (
    LOG_NAME,
    LOG_SEED,
    WITNESS_NAME,
    WITNESS_SEED,
    _checkpoint,
    _client,
    _pub,
    _RecordingHarness,
    _WitnessHarness,
)

SIGNER = NoteSigner(LOG_NAME, LOG_SEED)


def _leaves(n: int) -> list[bytes]:
    return [f"event-{i}".encode() for i in range(n)]


def _proof(old: int, new: int) -> list[bytes]:
    return consistency_proof(old, [leaf_hash(leaf) for leaf in _leaves(new)])


def _size(note: str) -> int:
    parsed = parse_checkpoint(verify_note(note, SIGNER.verifier_key))
    assert parsed is not None
    return parsed.size


def _fixed_client(
    status: int, text: str = "", headers: dict[str, str] | None = None
) -> tuple[WitnessClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, text=text, headers=headers or {})

    client = WitnessClient(
        "https://witness.example/submit",
        SIGNER.verifier_key,
        WitnessIdentity(WITNESS_NAME, _pub(WITNESS_SEED)),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return client, seen


# --- B1: proof size limit and malformed proofs, refused before any request ----------


@pytest.mark.parametrize("count", [0, 1, 62, 63])
def test_b1_up_to_63_nodes_decode(count: int) -> None:
    assert _decode_consistency_proof([bytes(32)] * count) == [bytes(32)] * count
    encoded = [base64.b64encode(bytes([i]) * 32).decode() for i in range(count)]
    assert len(_decode_consistency_proof(encoded)) == count


@pytest.mark.parametrize("count", [64, 65, 200])
def test_b1_more_than_63_nodes_are_refused(count: int) -> None:
    with pytest.raises(WitnessError, match="more than 63"):
        _decode_consistency_proof([bytes(32)] * count)


@pytest.mark.parametrize(
    ("count", "message"), [(62, "not consistent"), (63, "not consistent"), (64, "more than 63")]
)
def test_b1_boundary_through_submit_never_reaches_the_network(count: int, message: str) -> None:
    """62 and 63 nodes pass the size limit and fail only the local proof check.

    64 nodes fail the limit itself.
    """
    harness = _WitnessHarness()
    client = _client(harness)
    first = client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    with pytest.raises(WitnessError, match=message):
        client.submit(_checkpoint(SIGNER, _leaves(5)), [bytes(32)] * count)
    assert harness.requests == 1
    assert client.last_checkpoint == first


def test_b1_empty_proof_is_valid_only_where_the_spec_allows_it() -> None:
    harness = _RecordingHarness()
    client = _client(harness)
    client.submit(_checkpoint(SIGNER, _leaves(1)), [])  # first contact: old 0
    client.submit(_checkpoint(SIGNER, _leaves(1)), [])  # same checkpoint again
    assert harness.bodies[0].startswith("old 0\n\n")
    assert harness.bodies[1].startswith("old 1\n\n")
    with pytest.raises(WitnessError, match="not consistent"):
        client.submit(_checkpoint(SIGNER, _leaves(2)), [])  # growth needs a proof
    assert harness.requests == 2


@pytest.mark.parametrize(
    ("proof", "message"),
    [
        pytest.param([b""], "exactly 32 bytes", id="empty-node-bytes"),
        pytest.param([""], "exactly 32 bytes", id="empty-node-str"),
        pytest.param([bytes(31)], "exactly 32 bytes", id="31-bytes"),
        pytest.param([bytes(33)], "exactly 32 bytes", id="33-bytes"),
        pytest.param([base64.b64encode(bytes(31)).decode()], "exactly 32 bytes", id="b64-31"),
        pytest.param(["not-base64!"], "invalid base64", id="bad-alphabet"),
        pytest.param(["AAAA AAAA"], "invalid base64", id="space"),
        pytest.param(
            [base64.b64encode(bytes(32)).decode().rstrip("=")], "invalid base64", id="no-padding"
        ),
        pytest.param([base64.b64encode(bytes(32)).decode() + "\n"], "invalid base64", id="newline"),
        pytest.param(
            [base64.urlsafe_b64encode(b"\xff" * 32).decode()], "invalid base64", id="urlsafe"
        ),
        pytest.param([7], "bytes or base64 strings", id="int-node"),
        pytest.param([None], "bytes or base64 strings", id="none-node"),
        pytest.param(bytes(32), "sequence of 32-byte nodes", id="bytes-not-sequence"),
        pytest.param(
            base64.b64encode(bytes(32)).decode(), "sequence of 32-byte nodes", id="str-not-sequence"
        ),
        pytest.param({"a": 1}, "sequence of 32-byte nodes", id="mapping"),
    ],
)
def test_b1_malformed_proofs_are_refused_before_any_request(proof: object, message: str) -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    first = client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    with pytest.raises(WitnessError, match=message):
        client.submit(_checkpoint(SIGNER, _leaves(2)), proof)  # type: ignore[arg-type]
    assert harness.requests == 1
    assert client.last_checkpoint == first


def test_b1_non_canonical_base64_is_refused() -> None:
    # Same 32 bytes, but the last character carries non-zero unused bits.
    canonical = base64.b64encode(bytes(32)).decode()
    non_canonical = canonical[:-2] + "B="
    assert base64.b64decode(non_canonical) == bytes(32)
    with pytest.raises(WitnessError, match="non-canonical"):
        _decode_consistency_proof([non_canonical])


# --- B2: HTTP 409 and the reported witness size --------------------------------------


@pytest.mark.parametrize(
    ("headers", "text", "expected"),
    [
        pytest.param({"Content-Type": "text/x.tlog.size"}, "0\n", 0, id="zero"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7\n", 7, id="positive"),
        pytest.param(
            {"Content-Type": "text/x.tlog.size"},
            "18446744073709551615\n",
            (1 << 64) - 1,
            id="uint64-max",
        ),
        pytest.param(
            {"Content-Type": "text/x.tlog.size; charset=utf-8"}, "7\n", 7, id="with-parameter"
        ),
        pytest.param({"Content-Type": "TEXT/X.TLOG.SIZE"}, "7\n", 7, id="media-type-case"),
        pytest.param({}, "7\n", None, id="missing-header"),
        pytest.param({"Content-Type": "text/plain"}, "7\n", None, id="other-media-type"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "-1\n", None, id="negative"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "abc\n", None, id="non-numeric"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7.0\n", None, id="decimal-point"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, " 7\n", None, id="leading-space"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7 \n", None, id="trailing-space"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7\n\n", None, id="extra-line"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7\r\n", None, id="crlf"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "007\n", None, id="leading-zeros"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "７\n", None, id="fullwidth-digit"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "", None, id="empty-body"),
        pytest.param({"Content-Type": "text/x.tlog.size"}, "7", None, id="no-newline"),
    ],
)
def test_b2_409_reported_size(headers: dict[str, str], text: str, expected: int | None) -> None:
    client, seen = _fixed_client(409, text, headers)
    with pytest.raises(WitnessConflict) as caught:
        client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    # Zero is a size, not "no size".
    if expected is None:
        assert caught.value.witness_size is None
    else:
        assert caught.value.witness_size == expected
        assert caught.value.witness_size is not None
    assert len(seen) == 1
    assert client.last_checkpoint is None


@pytest.mark.parametrize("witness_size", [0, 1, 5, 9])
def test_b2_409_never_advances_or_rewinds_local_state(witness_size: int) -> None:
    """Whatever size the witness reports, smaller or larger than ours, the
    client keeps its state and does not retry on its own."""
    harness = _WitnessHarness()
    client = _client(harness)
    client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    second = client.submit(_checkpoint(SIGNER, _leaves(2)), _proof(1, 2))
    # The witness now claims a different state than ours.
    harness.latest = _checkpoint(SIGNER, _leaves(witness_size)) if witness_size else None
    requests = harness.requests
    with pytest.raises(WitnessConflict) as caught:
        client.submit(_checkpoint(SIGNER, _leaves(3)), _proof(2, 3))
    assert caught.value.witness_size == witness_size
    assert harness.requests == requests + 1
    assert client.last_checkpoint == second
    assert _size(client.last_checkpoint) == 2


@pytest.mark.parametrize("status", [400, 403, 404, 422, 500, 503])
def test_b2_other_errors_are_not_conflicts_and_change_nothing(status: int) -> None:
    client, seen = _fixed_client(status, "7\n", {"Content-Type": "text/x.tlog.size"})
    with pytest.raises(WitnessError, match=f"HTTP {status}") as caught:
        client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    assert not isinstance(caught.value, WitnessConflict)
    assert len(seen) == 1
    assert client.last_checkpoint is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "— witness.example/test AAAA",
        "garbage\n",
        "— other.example/w " + base64.b64encode(bytes(76)).decode() + "\n",
    ],
)
def test_b2_malformed_200_responses_change_nothing(text: str) -> None:
    client, _ = _fixed_client(200, text)
    with pytest.raises(WitnessError):
        client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    assert client.last_checkpoint is None


def test_b2_transport_error_changes_nothing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = WitnessClient(
        "https://witness.example/submit",
        SIGNER.verifier_key,
        WitnessIdentity(WITNESS_NAME, _pub(WITNESS_SEED)),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WitnessError, match="request failed"):
        client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    assert client.last_checkpoint is None


# --- B3: the checkpoint sequence -------------------------------------------------------


def test_b3_first_contact_with_checkpoint_1() -> None:
    harness = _RecordingHarness()
    client = _client(harness)
    result = client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    assert harness.bodies == ["old 0\n\n" + _checkpoint(SIGNER, _leaves(1))]
    assert _size(result) == 1


def test_b3_first_contact_without_checkpoint_1() -> None:
    """The witness has never seen size 1: first contact at size 5 is "old 0" with no proof."""
    harness = _RecordingHarness()
    client = _client(harness)
    result = client.submit(_checkpoint(SIGNER, _leaves(5)), [])
    assert harness.bodies[0].startswith("old 0\n\n")
    assert _size(result) == 5


def test_b3_first_contact_with_a_proof_is_refused() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    with pytest.raises(WitnessError, match="initial checkpoint must use an empty"):
        client.submit(_checkpoint(SIGNER, _leaves(2)), _proof(1, 2))
    assert harness.requests == 0


def test_b3_empty_tree_then_size_zero_again_then_size_2() -> None:
    harness = _RecordingHarness()
    client = _client(harness)
    empty = SIGNER.sign(Checkpoint(LOG_NAME, 0, empty_root()).body())
    assert _size(client.submit(empty, [])) == 0
    assert _size(client.submit(empty, [])) == 0  # repetition of size 0
    # From size 0 the consistency proof is empty by definition.
    with pytest.raises(
        WitnessError, match="size-zero checkpoint must use the empty root and proof"
    ):
        client.submit(_checkpoint(SIGNER, _leaves(2)), [bytes(32)])
    assert _size(client.submit(_checkpoint(SIGNER, _leaves(2)), [])) == 2
    assert [body.split("\n", 1)[0] for body in harness.bodies] == ["old 0", "old 0", "old 0"]


def test_b3_progression_1_to_2_then_gap_to_7() -> None:
    harness = _RecordingHarness()
    client = _client(harness)
    client.submit(_checkpoint(SIGNER, _leaves(1)), [])
    assert _size(client.submit(_checkpoint(SIGNER, _leaves(2)), _proof(1, 2))) == 2
    assert _size(client.submit(_checkpoint(SIGNER, _leaves(7)), _proof(2, 7))) == 7
    assert [body.split("\n", 1)[0] for body in harness.bodies] == ["old 0", "old 1", "old 2"]


def test_b3_gap_with_a_proof_for_another_size_is_refused() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    first = client.submit(_checkpoint(SIGNER, _leaves(2)), [])
    with pytest.raises(WitnessError, match="not consistent"):
        client.submit(_checkpoint(SIGNER, _leaves(7)), _proof(3, 7))
    assert harness.requests == 1
    assert client.last_checkpoint == first


def test_b3_repetition_of_the_same_checkpoint() -> None:
    harness = _RecordingHarness()
    client = _client(harness)
    note = _checkpoint(SIGNER, _leaves(3))
    client.submit(note, [])
    assert _size(client.submit(note, [])) == 3
    assert harness.bodies[1] == "old 3\n\n" + note
    with pytest.raises(WitnessError, match="same-size checkpoint does not match"):
        client.submit(note, [bytes(32)])
    assert harness.requests == 2


def test_b3_regression_is_refused_before_any_request() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    latest = client.submit(_checkpoint(SIGNER, _leaves(3)), [])
    for smaller in (2, 1, 0):
        with pytest.raises(WitnessError, match="rollback"):
            client.submit(_checkpoint(SIGNER, _leaves(smaller)), [])
    assert harness.requests == 1
    assert client.last_checkpoint == latest


def test_b3_same_size_with_another_root_is_refused() -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    client.submit(_checkpoint(SIGNER, _leaves(3)), [])
    forked = _checkpoint(SIGNER, [b"x", b"y", b"z"])
    with pytest.raises(WitnessError, match="same-size checkpoint does not match"):
        client.submit(forked, [])
    assert harness.requests == 1


@pytest.mark.parametrize(
    "previous",
    [
        pytest.param(
            lambda: NoteSigner("other.example/log", LOG_SEED).sign(
                Checkpoint("other.example/log", 1, bytes(32)).body()
            ),
            id="other-log",
        ),
        pytest.param(
            lambda: NoteSigner(LOG_NAME, bytes(32)).sign(Checkpoint(LOG_NAME, 1, bytes(32)).body()),
            id="other-key",
        ),
        pytest.param(lambda: "not a note", id="garbage"),
    ],
)
def test_b3_incompatible_previous_state_is_refused(previous: object) -> None:
    harness = _WitnessHarness()
    client = _client(harness)
    with pytest.raises(WitnessError, match="previous checkpoint is invalid"):
        client.submit(_checkpoint(SIGNER, _leaves(2)), [], previous_checkpoint=previous())  # type: ignore[operator]
    assert harness.requests == 0
    assert client.last_checkpoint is None


def test_b3_witness_ahead_of_a_fresh_client_reports_its_size() -> None:
    """In-memory client state is lost on restart: the witness answers 409 with its size."""
    harness = _WitnessHarness()
    _client(harness).submit(_checkpoint(SIGNER, _leaves(4)), [])
    restarted = _client(harness)
    with pytest.raises(WitnessConflict) as caught:
        restarted.submit(_checkpoint(SIGNER, _leaves(5)), [])
    assert caught.value.witness_size == 4
    assert restarted.last_checkpoint is None
    # Resuming from the witness's checkpoint (supplied by the operator) works.
    resumed = restarted.submit(
        _checkpoint(SIGNER, _leaves(5)), _proof(4, 5), previous_checkpoint=harness.latest
    )
    assert _size(resumed) == 5
