import pytest

from ayorai_attractor.replay import ReplayBundle
from ayorai_attractor.replay_store import ReplayStore


def test_replay_store_round_trip_and_deduplication(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))
    bundle = ReplayBundle.build(
        "tr_replay",
        [{"event": "verified", "value": "ok"}],
    )

    assert store.put(bundle) == bundle.digest
    assert store.put(bundle) == bundle.digest

    loaded = store.get(bundle.digest)
    assert loaded == bundle
    assert loaded is not None
    assert loaded.verify()


def test_replay_store_returns_none_for_unknown_digest(tmp_path) -> None:
    assert ReplayStore(str(tmp_path)).get("0" * 64) is None


def test_replay_store_rejects_invalid_digest(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))

    with pytest.raises(ValueError):
        store.get("../outside")

    with pytest.raises(ValueError):
        store.get("ABC")


def test_replay_store_rejects_digest_mismatch(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))
    bundle = ReplayBundle.build(
        "tr_replay",
        [{"event": "verified", "value": "ok"}],
    )
    store.put(bundle)

    source = tmp_path / f"{bundle.digest}.json"
    target = tmp_path / f"{'f' * 64}.json"
    target.write_bytes(source.read_bytes())

    with pytest.raises(ValueError, match="mismatch"):
        store.get("f" * 64)


def test_replay_store_put_rejects_forged_digest_without_writing(tmp_path) -> None:
    store_dir = tmp_path / "replays"
    store = ReplayStore(str(store_dir))
    bundle = ReplayBundle.build("tr_replay", [{"event": "verified"}])
    forged = ReplayBundle(bundle.version, bundle.trace_id, bundle.events, "0" * 64)
    traversal = ReplayBundle(bundle.version, bundle.trace_id, bundle.events, "../outside")

    for candidate in (forged, traversal):
        with pytest.raises(ValueError, match="does not match"):
            store.put(candidate)

    assert list(store_dir.iterdir()) == []
    assert not (tmp_path / "outside.json").exists()


def test_replay_store_failed_write_leaves_no_partial_file(tmp_path, monkeypatch) -> None:
    import os

    store = ReplayStore(str(tmp_path))
    bundle = ReplayBundle.build("tr_replay", [{"event": "verified"}])

    def crash(*_args: object) -> None:
        raise OSError("disk failure")

    monkeypatch.setattr(os, "replace", crash)
    with pytest.raises(OSError, match="disk failure"):
        store.put(bundle)
    monkeypatch.undo()

    assert list(tmp_path.iterdir()) == []
    assert store.get(bundle.digest) is None
    assert store.put(bundle) == bundle.digest
    assert store.get(bundle.digest) == bundle
